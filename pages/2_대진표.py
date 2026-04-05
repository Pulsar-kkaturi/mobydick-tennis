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

    # ── 대진 자동 생성 ────────────────────────────────────────────────────────
    with st.expander("대진 자동 생성"):
        players = db.get_tournament_players(tid)

        if len(players) < 2:
            st.warning("자동 생성은 선수 2명 이상이 필요합니다.")
        else:
            wc_map = {p["name"]: p["is_wildcard"] for p in players}

            col_a, col_b = st.columns(2)
            with col_a:
                match_type = st.radio(
                    "경기 방식",
                    ["복식", "단식"],
                    horizontal=True,
                    key="gen_match_type",
                )
            with col_b:
                randomize = st.checkbox("선수 순서 랜덤 섞기", value=True, key="gen_randomize")

            col_c, col_d = st.columns(2)
            with col_c:
                court_count = st.slider("코트 수", min_value=1, max_value=4, value=2, key="gen_courts")
            with col_d:
                matches_per_person = st.number_input(
                    "인당 경기 수",
                    min_value=1, max_value=20, value=3, step=1, key="gen_mpp",
                )

            courts = ["A", "B", "C", "D"][:court_count]
            players_per_match = 4 if match_type == "복식" else 2
            min_required = players_per_match  # 최소 1경기 가능 인원

            # 예상 라운드 수 미리 표시
            import math
            n = len(players)
            active_per_round = court_count * players_per_match
            active_per_round = (min(active_per_round, n) // players_per_match) * players_per_match
            if active_per_round > 0:
                total_slots = n * matches_per_person
                est_rounds = math.ceil(total_slots / active_per_round)
                st.caption(
                    f"선수 {n}명 · 코트 {court_count}개 · {match_type} → "
                    f"라운드당 {active_per_round}명 활동 · 예상 **{est_rounds}라운드**"
                )
            else:
                st.warning(f"{match_type} 경기를 위해 선수가 더 필요합니다.")

            if n < min_required:
                st.warning(f"{match_type} 경기를 위해 최소 {min_required}명이 필요합니다.")
            elif st.button("대진 생성", key="gen_btn", type="primary"):
                schedule = generate_schedule(
                    players,
                    courts=courts,
                    match_type=match_type,
                    matches_per_person=int(matches_per_person),
                    randomize=randomize,
                )

                if not schedule:
                    st.error("대진을 생성할 수 없습니다. 선수 수나 설정을 확인해 주세요.")
                else:
                    # WC 정보 기반 match_type 상세 표기 (단식은 그대로)
                    if match_type == "복식":
                        for m in schedule:
                            t1 = [m["team1_player1"], m.get("team1_player2")]
                            t2 = [m["team2_player1"], m.get("team2_player2")]
                            m["match_type"] = infer_match_type(t1, t2, wc_map)

                    for m in schedule:
                        db.upsert_match(tid, m)

                    st.success(f"{len(schedule)}경기 생성 완료! (총 {schedule[-1]['round']} 까지)")
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
