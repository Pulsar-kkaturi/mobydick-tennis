"""
대진표 페이지
- 라운드별 경기 목록 보기
- 대진 자동 생성 (단식/복식, 코트 수, 인당 경기 수 기반)
- 수동으로 경기 추가 / 삭제
"""
import streamlit as st
import db
from logic.schedule import generate_schedule, infer_match_type

st.title("대진표")

tournament = db.render_tournament_selector()
if not tournament:
    st.stop()

selected_name = tournament["name"]
tid = tournament["id"]

# 레거시 대회는 대진표 불필요
if tournament.get("is_legacy"):
    st.info("레거시 대회는 대진표가 없습니다. 순위표 페이지에서 1~3위를 직접 기록해 주세요.")
    st.stop()

# 완료/승인된 대회는 수정 잠금
is_locked = tournament.get("is_finished") or tournament.get("is_approved")
if is_locked:
    lock_reason = "승인된" if tournament.get("is_approved") else "완료 처리된"
    st.warning(f"🔒 {lock_reason} 대회입니다. 대진표를 추가하거나 삭제할 수 없습니다.")

# ── 현재 대진표 표시 ──────────────────────────────────────────────────────────
st.subheader(f"{selected_name} 대진표")
matches = db.get_matches(tid)

if matches:
    # 라운드별로 그룹핑
    rounds: dict[str, list] = {}
    for m in matches:
        rounds.setdefault(m["round"], []).append(m)

    for round_name, round_matches in sorted(rounds.items()):
        st.markdown(f"### {round_name}")
        for m in round_matches:
            t1 = f"{m['team1_player1']}" + (f" / {m['team1_player2']}" if m.get("team1_player2") else "")
            t2 = f"{m['team2_player1']}" + (f" / {m['team2_player2']}" if m.get("team2_player2") else "")
            s1 = m["team1_score"] if m["team1_score"] is not None else "-"
            s2 = m["team2_score"] if m["team2_score"] is not None else "-"

            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.write(f"**코트 {m['court']}** | {t1}  vs  {t2}  ({s1} : {s2})")
            with col2:
                st.caption(m.get("match_type") or "")
            with col3:
                if is_locked:
                    st.button("삭제", key=f"del_match_{m['id']}", disabled=True,
                              help="완료 또는 승인된 대회는 경기를 삭제할 수 없습니다.")
                else:
                    if st.button("삭제", key=f"del_match_{m['id']}"):
                        db.delete_match(m["id"])
                        st.rerun()
else:
    st.info("아직 대진이 없습니다. 아래에서 자동 생성하거나 수동으로 추가하세요.")

st.divider()

# 잠금 상태면 대진 생성·추가 섹션 자체를 숨김
if not is_locked:
    # ── 대진 일괄 삭제 ────────────────────────────────────────────────────────
    if matches:
        with st.expander("⚠️ 대진 일괄 삭제"):
            st.warning("경기 결과(점수)를 포함한 **모든 경기**가 삭제됩니다.")
            if st.button("전체 삭제 확인", key="delete_all_btn", type="primary"):
                db.delete_all_matches(tid)
                st.success("모든 경기를 삭제했습니다.")
                st.rerun()

if not is_locked:

    # ── 대진 자동 생성 ────────────────────────────────────────────────────────
    with st.expander("대진 자동 생성"):
        import math
        players = db.get_tournament_players(tid)
        n = len(players)

        if n < 2:
            st.warning("자동 생성은 선수 2명 이상이 필요합니다.")
        else:
            wc_map = {p["name"]: p["is_wildcard"] for p in players}

            col_a, col_b = st.columns(2)
            with col_a:
                match_type = st.radio(
                    "경기 방식", ["복식", "단식"],
                    horizontal=True, key="gen_match_type",
                )
            with col_b:
                randomize = st.checkbox("선수 순서 랜덤 섞기", value=True, key="gen_randomize")

            col_c, col_d = st.columns(2)
            with col_c:
                court_count = st.slider("코트 수", min_value=1, max_value=4, value=2, key="gen_courts")
            with col_d:
                matches_per_person = st.number_input(
                    "인당 경기 수", min_value=1, max_value=20, value=3, step=1, key="gen_mpp",
                )

            players_per_match = 4 if match_type == "복식" else 2

            # 실제 사용 가능한 코트 수: 선수 수 ÷ 코트당 필요 인원
            actual_courts = min(court_count, n // players_per_match)
            actual_court_labels = ["A", "B", "C", "D"][:actual_courts]
            actual_active = actual_courts * players_per_match

            # ── 예상 결과 미리보기 ────────────────────────────────────────────
            if actual_courts == 0:
                st.error(
                    f"⛔ {match_type} 1경기에 {players_per_match}명이 필요합니다. "
                    f"현재 배정 선수: **{n}명** (부족)"
                )
            else:
                if actual_courts < court_count:
                    st.warning(
                        f"⚠️ 코트 {court_count}개 요청 → 선수 {n}명으로는 "
                        f"**코트 {actual_courts}개** ({', '.join(actual_court_labels)})만 사용 가능합니다. "
                        f"({match_type} 코트 1개당 {players_per_match}명 필요)"
                    )

                sitting_per_round = n - actual_active
                est_rounds = math.ceil((n * int(matches_per_person)) / actual_active)
                st.info(
                    f"선수 **{n}명** · 코트 **{actual_courts}개** "
                    f"({', '.join(actual_court_labels)}) · {match_type}  \n"
                    f"라운드당 **{actual_active}명** 활동"
                    + (f" / **{sitting_per_round}명** 휴식" if sitting_per_round > 0 else " (전원 참가)")
                    + f" · 예상 **{est_rounds}라운드**"
                )

                # 기존 경기 여부 안내
                existing_matches = db.get_matches(tid)
                if existing_matches:
                    has_scores = any(m["team1_score"] is not None for m in existing_matches)
                    if has_scores:
                        st.warning(
                            f"⚠️ 현재 {len(existing_matches)}개 경기 중 점수가 입력된 경기가 있습니다. "
                            "재생성 시 **모든 경기와 점수가 삭제**됩니다."
                        )
                    else:
                        st.info(f"기존 {len(existing_matches)}개 경기를 삭제 후 새로 생성합니다.")

                if st.button("대진 생성 (기존 경기 초기화)", key="gen_btn", type="primary"):
                    schedule = generate_schedule(
                        players,
                        courts=actual_court_labels,   # 실제 사용 코트 목록 사용
                        match_type=match_type,
                        matches_per_person=int(matches_per_person),
                        randomize=randomize,
                    )

                    if not schedule:
                        st.error("대진을 생성할 수 없습니다. 선수 수나 설정을 확인해 주세요.")
                    else:
                        db.delete_all_matches(tid)

                        if match_type == "복식":
                            for m in schedule:
                                t1 = [m["team1_player1"], m.get("team1_player2")]
                                t2 = [m["team2_player1"], m.get("team2_player2")]
                                m["match_type"] = infer_match_type(t1, t2, wc_map)

                        for m in schedule:
                            db.upsert_match(tid, m)

                        st.success(f"{len(schedule)}경기 생성 완료! ({schedule[-1]['round']} 까지)")
                        st.rerun()

    # ── 경기 수동 추가 ────────────────────────────────────────────────────────
    with st.expander("경기 수동 추가"):
        players = db.get_tournament_players(tid)
        player_names = ["(없음)"] + [p["name"] for p in players]

        col1, col2, col3 = st.columns(3)
        with col1:
            # 라운드: 숫자 입력 (min 1), "R{n}" 형태로 저장
            round_num = st.number_input("라운드 번호", min_value=1, step=1, value=1, key="manual_round")
        with col2:
            court_sel = st.radio("코트", ["A", "B", "C", "D"], horizontal=True, key="manual_court")
        with col3:
            mtype_sel = st.radio("경기유형", ["복식", "단식"], horizontal=True, key="manual_mtype")

        is_doubles = mtype_sel == "복식"

        st.markdown("**팀 1**")
        c1, c2 = st.columns(2)
        p1 = c1.selectbox("선수1", player_names, key="m_p1")
        p2 = c2.selectbox("선수2", player_names, key="m_p2",
                          disabled=not is_doubles,
                          help="복식일 때만 입력" if not is_doubles else None)

        st.markdown("**팀 2**")
        c3, c4 = st.columns(2)
        p3 = c3.selectbox("선수1", player_names, key="m_p3")
        p4 = c4.selectbox("선수2", player_names, key="m_p4",
                          disabled=not is_doubles,
                          help="복식일 때만 입력" if not is_doubles else None)

        if st.button("추가", key="manual_add_btn"):
            if p1 == "(없음)" or p3 == "(없음)":
                st.error("각 팀에 최소 1명의 선수가 필요합니다.")
            elif is_doubles and (p2 == "(없음)" or p4 == "(없음)"):
                st.error("복식은 각 팀에 2명이 필요합니다.")
            else:
                db.upsert_match(tid, {
                    "round": f"R{int(round_num)}",
                    "court": court_sel,
                    "team1_player1": p1,
                    "team1_player2": None if (not is_doubles or p2 == "(없음)") else p2,
                    "team2_player1": p3,
                    "team2_player2": None if (not is_doubles or p4 == "(없음)") else p4,
                    "team1_score": None,
                    "team2_score": None,
                    "match_type": mtype_sel,
                })
                st.success("추가했습니다.")
                st.rerun()
