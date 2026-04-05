"""
경기 결과 입력 페이지
- 라운드별로 경기를 선택하고 점수 입력
- 저장 즉시 순위표에 반영
"""
import streamlit as st
import db

st.set_page_config(page_title="경기 입력", page_icon="✏️")
st.title("경기 결과 입력")

# ── 사이드바: 대회 선택 ───────────────────────────────────────────────────────
tournaments = db.get_tournaments()
if not tournaments:
    st.warning("먼저 홈에서 대회를 만들어 주세요.")
    st.stop()

t_names = [t["name"] for t in tournaments]
selected_name = st.sidebar.selectbox("대회 선택", t_names)
tournament = next(t for t in tournaments if t["name"] == selected_name)
tid = tournament["id"]

# 레거시 대회는 경기 입력 불필요
if tournament.get("is_legacy"):
    st.info("레거시 대회는 경기 입력이 없습니다. 순위표 페이지에서 1~3위를 직접 기록해 주세요.")
    st.stop()

# ── 경기 목록 ─────────────────────────────────────────────────────────────────
matches = db.get_matches(tid)
if not matches:
    st.info("대진표가 없습니다. 먼저 대진표 페이지에서 경기를 만들어 주세요.")
    st.stop()

# 라운드 선택 필터
rounds = sorted(set(m["round"] for m in matches))
selected_round = st.selectbox("라운드 선택", ["전체"] + rounds)

filtered = matches if selected_round == "전체" else [m for m in matches if m["round"] == selected_round]

# 미입력 경기만 보기 옵션
show_pending = st.checkbox("미입력 경기만 보기", value=False)
if show_pending:
    filtered = [m for m in filtered if m["team1_score"] is None]

st.divider()

# ── 각 경기 점수 입력 ─────────────────────────────────────────────────────────
for m in filtered:
    t1 = m["team1_player1"] + (f" / {m['team1_player2']}" if m.get("team1_player2") else "")
    t2 = m["team2_player1"] + (f" / {m['team2_player2']}" if m.get("team2_player2") else "")

    with st.container(border=True):
        st.markdown(f"**{m['round']} - 코트 {m['court']}** &nbsp; `{m.get('match_type', '')}`")
        st.markdown(f"**{t1}** &nbsp; vs &nbsp; **{t2}**")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            s1 = st.number_input(
                f"{t1} 점수",
                min_value=0, max_value=99,
                value=int(m["team1_score"]) if m["team1_score"] is not None else 0,
                key=f"s1_{m['id']}",
                label_visibility="collapsed",
            )
        with col2:
            s2 = st.number_input(
                f"{t2} 점수",
                min_value=0, max_value=99,
                value=int(m["team2_score"]) if m["team2_score"] is not None else 0,
                key=f"s2_{m['id']}",
                label_visibility="collapsed",
            )
        with col3:
            if st.button("저장", key=f"save_{m['id']}"):
                db.upsert_match(tid, {
                    "team1_score": s1,
                    "team2_score": s2,
                }, match_id=m["id"])
                st.toast(f"저장 완료! ({t1} {s1} : {s2} {t2})")
                st.rerun()

        # 현재 저장된 점수 표시
        if m["team1_score"] is not None:
            st.caption(f"저장된 점수: {m['team1_score']} : {m['team2_score']}")

# ── 추가 점수 입력 ────────────────────────────────────────────────────────────
st.divider()
with st.expander("추가 점수 입력 (토너먼트 보너스 등)"):
    players = db.get_tournament_players(tid)
    extra_scores = db.get_extra_scores(tid)
    extra_map = {e["player_name"]: e for e in extra_scores}

    st.caption("토너먼트 진출 보너스 등 수동으로 점수를 추가할 수 있습니다.")

    for p in players:
        existing = extra_map.get(p["name"])
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.write(p["name"])
        with col2:
            score_val = st.number_input(
                "추가 점수",
                min_value=-999, max_value=9999,
                value=existing["score"] if existing else 0,
                key=f"extra_{p['name']}",
                label_visibility="collapsed",
            )
        with col3:
            note_val = st.text_input(
                "사유",
                value=existing["note"] if existing else "",
                key=f"note_{p['name']}",
                label_visibility="collapsed",
                placeholder="사유 (선택)",
            )

    if st.button("추가 점수 전체 저장"):
        for p in players:
            existing = extra_map.get(p["name"])
            score_val = st.session_state.get(f"extra_{p['name']}", 0)
            note_val = st.session_state.get(f"note_{p['name']}", "")
            db.upsert_extra_score(
                tid, p["name"], score_val, note_val,
                score_id=existing["id"] if existing else None,
            )
        st.success("저장했습니다.")
        st.rerun()
