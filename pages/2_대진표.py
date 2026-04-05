"""
대진표 페이지
- 라운드별 경기 목록 보기
- 대진 자동 생성 (라운드 로빈)
- 수동으로 경기 추가 / 삭제
"""
import streamlit as st
import db
from logic.schedule import generate_doubles_schedule, infer_match_type

st.title("대진표")

# 사이드바에서 선택한 대회를 session_state에서 읽어옴
tournament = st.session_state.get("selected_tournament")
if not tournament:
    st.warning("사이드바에서 대회를 선택해 주세요.")
    st.stop()

selected_name = tournament["name"]
tid = tournament["id"]

# 레거시 대회는 대진표 불필요
if tournament.get("is_legacy"):
    st.info("레거시 대회는 대진표가 없습니다. 순위표 페이지에서 1~3위를 직접 기록해 주세요.")
    st.stop()

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
                if st.button("삭제", key=f"del_match_{m['id']}"):
                    db.delete_match(m["id"])
                    st.rerun()
else:
    st.info("아직 대진이 없습니다. 아래에서 자동 생성하거나 수동으로 추가하세요.")

st.divider()

# ── 대진 자동 생성 ────────────────────────────────────────────────────────────
with st.expander("대진 자동 생성 (라운드 로빈)"):
    players = db.get_tournament_players(tid)
    if len(players) < 4:
        st.warning("자동 생성은 선수 4명 이상이 필요합니다.")
    else:
        courts_input = st.text_input("코트 목록 (쉼표로 구분)", value="A, B")
        courts = [c.strip() for c in courts_input.split(",") if c.strip()]
        randomize = st.checkbox("선수 순서 랜덤 섞기", value=True)

        if st.button("대진 생성"):
            wc_map = {p["name"]: p["is_wildcard"] for p in players}
            schedule = generate_doubles_schedule(players, courts=courts, randomize=randomize)
            # match_type 자동 추론
            for m in schedule:
                t1 = [m["team1_player1"], m["team1_player2"]]
                t2 = [m["team2_player1"], m["team2_player2"]]
                m["match_type"] = infer_match_type(t1, t2, wc_map)

            for m in schedule:
                db.upsert_match(tid, m)

            st.success(f"{len(schedule)}경기 생성 완료!")
            st.rerun()

# ── 경기 수동 추가 ────────────────────────────────────────────────────────────
with st.expander("경기 수동 추가"):
    players = db.get_tournament_players(tid)
    player_names = ["(없음)"] + [p["name"] for p in players]

    with st.form("add_match_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            round_input = st.text_input("라운드", value="R1")
            court_input = st.text_input("코트", value="A")
        with col2:
            match_type_input = st.text_input("경기 유형", value="복식")

        st.markdown("**팀 1**")
        c1, c2 = st.columns(2)
        p1 = c1.selectbox("선수1", player_names, key="m_p1")
        p2 = c2.selectbox("선수2 (단식이면 없음)", player_names, key="m_p2")

        st.markdown("**팀 2**")
        c3, c4 = st.columns(2)
        p3 = c3.selectbox("선수1", player_names, key="m_p3")
        p4 = c4.selectbox("선수2 (단식이면 없음)", player_names, key="m_p4")

        if st.form_submit_button("추가"):
            if p1 == "(없음)" or p3 == "(없음)":
                st.error("각 팀에 최소 1명의 선수가 필요합니다.")
            else:
                db.upsert_match(tid, {
                    "round": round_input,
                    "court": court_input,
                    "team1_player1": p1,
                    "team1_player2": None if p2 == "(없음)" else p2,
                    "team2_player1": p3,
                    "team2_player2": None if p4 == "(없음)" else p4,
                    "team1_score": None,
                    "team2_score": None,
                    "match_type": match_type_input,
                })
                st.success("추가했습니다.")
                st.rerun()
