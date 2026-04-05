"""
모비딕 테니스 - 메인 홈 화면
- 시즌 전체 랭킹 (대회 선택 가능)
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
    # 멀티셀렉트로 포함할 대회 선택
    t_names = [t["name"] for t in tournaments]
    selected_for_ranking = st.multiselect(
        "랭킹 산정에 포함할 대회 선택",
        options=t_names,
        default=t_names,  # 기본값: 전체 선택
    )

    selected_tournaments = [t for t in tournaments if t["name"] in selected_for_ranking]

    if not selected_tournaments:
        st.warning("대회를 1개 이상 선택해 주세요.")
    else:
        # 선택된 대회들의 순위표 계산
        standings_map = {}
        for t in selected_tournaments:
            tid = t["id"]
            players = db.get_players(tid)
            matches = db.get_matches(tid)
            config = db.get_scoring_config(tid)
            extra_scores = db.get_extra_scores(tid)
            if players:
                standings_map[tid] = calculate_standings(players, matches, config, extra_scores)

        season_ranking = get_season_ranking(selected_tournaments, standings_map)

        if not season_ranking:
            st.info("아직 순위 포인트를 얻은 선수가 없습니다. (1~3위를 달성해야 포인트 부여)")
        else:
            # 시즌 랭킹 표
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
                    st.markdown(f"**{t['name']}** &nbsp; {status}")
                    if t.get("date"):
                        st.caption(f"날짜: {t['date']}")
                    if t.get("description"):
                        st.caption(t["description"])
                with c2:
                    # 선수 수 / 경기 수 표시
                    players_count = len(db.get_players(t["id"]))
                    matches_count = len(db.get_matches(t["id"]))
                    st.caption(f"선수 {players_count}명 / 경기 {matches_count}개")
                with c3:
                    # 완료 토글
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
        desc = st.text_area("메모 (선택)", height=80)

        if st.form_submit_button("대회 생성"):
            if not name.strip():
                st.error("대회 이름을 입력해 주세요.")
            else:
                db.create_tournament(name.strip(), str(date), desc.strip())
                st.success(f"'{name}' 대회를 만들었습니다!")
                st.rerun()
