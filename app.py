"""
모비딕 테니스 - 메인 홈 화면
- 시즌 전체 랭킹 (연도 필터)
- 대회 생성 / 관리
"""
import streamlit as st
import pandas as pd
import db
from logic.scoring import calculate_standings, get_season_ranking

st.set_page_config(
    page_title="모비딕 테니스",
    page_icon="🎾",
    layout="wide",
)

st.title("🎾 모비딕 테니스")
st.caption("대회 관리 & 순위 시스템")

# ── 대회 목록 로드 ────────────────────────────────────────────────────────────
tournaments = db.get_tournaments()

# ── 시즌 랭킹 섹션 ───────────────────────────────────────────────────────────
st.header("시즌 전체 랭킹")

if not tournaments:
    st.info("아직 대회가 없습니다. 아래에서 첫 번째 대회를 만들어 보세요!")
else:
    def get_year(t):
        """대회 날짜에서 연도 추출. 날짜 없으면 '날짜 미설정' 반환."""
        if t.get("date"):
            return str(t["date"])[:4]
        return "날짜 미설정"

    years = sorted({get_year(t) for t in tournaments}, reverse=True)
    selected_year = st.selectbox("연도 선택", ["전체"] + years, index=0)

    if selected_year == "전체":
        selected_tournaments = tournaments
    else:
        selected_tournaments = [t for t in tournaments if get_year(t) == selected_year]

    if not selected_tournaments:
        st.info(f"{selected_year}년에 해당하는 대회가 없습니다.")
    else:
        # 각 대회의 순위표 계산
        # - 일반 대회: 경기 결과로 계산
        # - 레거시 대회: 수동 입력한 1~3위 사용
        standings_map = {}
        for t in selected_tournaments:
            tid = t["id"]
            if t.get("is_legacy"):
                # 레거시: legacy_results 테이블에서 가져와 standings 형식으로 변환
                legacy = db.get_legacy_results(tid)
                RANK_POINTS = {1: 3, 2: 2, 3: 1}
                standings_map[tid] = [
                    {"name": r["player_name"], "rank": r["rank"]}
                    for r in legacy if r["rank"] in RANK_POINTS
                ]
            else:
                players = db.get_tournament_players(tid)
                matches = db.get_matches(tid)
                config = db.get_scoring_config(tid)
                extra_scores = db.get_extra_scores(tid)
                if players:
                    standings_map[tid] = calculate_standings(players, matches, config, extra_scores)

        season_ranking = get_season_ranking(selected_tournaments, standings_map)

        if not season_ranking:
            st.info("아직 순위 포인트를 얻은 선수가 없습니다. (1~3위를 달성해야 포인트 부여)")
        else:
            rows = []
            for i, r in enumerate(season_ranking):
                detail_str = " | ".join(
                    f"{tname}: {info['rank']}위 (+{info['pts']})"
                    for tname, info in r["detail"].items()
                )
                rows.append({
                    "시즌순위": i + 1,
                    "이름": r["name"],
                    "랭킹포인트": r["points"],
                    "상세": detail_str,
                })

            df = pd.DataFrame(rows)

            def highlight_top3(row):
                colors = {1: "background-color: #FFD700", 2: "background-color: #C0C0C0", 3: "background-color: #CD7F32"}
                return [colors.get(row["시즌순위"], "")] * len(row)

            st.dataframe(
                df.style.apply(highlight_top3, axis=1),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("랭킹 포인트: 각 대회 1위=3점 / 2위=2점 / 3위=1점 / 4위 이하=미부여")

st.divider()

# ── 대회 목록 & 관리 ─────────────────────────────────────────────────────────
st.header("대회 목록")

col_main, col_form = st.columns([3, 2])

with col_main:
    if not tournaments:
        st.info("대회가 없습니다.")
    else:
        for t in tournaments:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
                with c1:
                    status = "✅ 완료" if t["is_finished"] else "🔄 진행 중"
                    legacy_badge = " &nbsp; `레거시`" if t.get("is_legacy") else ""
                    st.markdown(f"**{t['name']}** &nbsp; {status}{legacy_badge}")
                    if t.get("date"):
                        st.caption(f"날짜: {t['date']}")
                    if t.get("description"):
                        st.caption(t["description"])
                with c2:
                    if t.get("is_legacy"):
                        # 레거시 대회는 기록된 순위 수 표시
                        results = db.get_legacy_results(t["id"])
                        st.caption(f"순위 기록: {len(results)}/3")
                    else:
                        players_count = len(db.get_tournament_players(t["id"]))
                        matches_count = len(db.get_matches(t["id"]))
                        st.caption(f"선수 {players_count}명 / 경기 {matches_count}개")
                with c3:
                    label = "완료 취소" if t["is_finished"] else "완료 처리"
                    if st.button(label, key=f"finish_{t['id']}"):
                        db.finish_tournament(t["id"], not t["is_finished"])
                        st.rerun()
                with c4:
                    if st.button("삭제", key=f"del_t_{t['id']}"):
                        if st.session_state.get(f"confirm_del_{t['id']}"):
                            db.delete_tournament(t["id"])
                            st.rerun()
                        else:
                            st.session_state[f"confirm_del_{t['id']}"] = True
                            st.warning("한 번 더 누르면 삭제됩니다.")

with col_form:
    st.subheader("새 대회 만들기")
    with st.form("create_tournament", clear_on_submit=True):
        name = st.text_input("대회 이름", placeholder="예: 2026 상반기 리그")
        date = st.date_input("대회 날짜 (선택)")
        desc = st.text_area("메모 (선택)", height=60)
        is_legacy = st.checkbox(
            "레거시 대회",
            help="대진표·경기 없이 1~3위만 기록하는 과거 대회용 모드",
        )

        if st.form_submit_button("대회 생성"):
            if not name.strip():
                st.error("대회 이름을 입력해 주세요.")
            else:
                db.create_tournament(name.strip(), str(date), desc.strip(), is_legacy)
                st.success(f"'{name}' 대회를 만들었습니다!")
                st.rerun()
