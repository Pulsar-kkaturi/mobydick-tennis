"""
대시보드 페이지 (메인 홈)
- 시즌 전체 랭킹 (연도 필터)
- 대회 목록 및 생성/삭제 (로그인 시 관리 기능 활성화)
"""
import streamlit as st
import pandas as pd
import db
import auth
from logic.scoring import calculate_standings, get_season_ranking

col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("Assets/LOGO_2026_HJA.png", width=90)
with col_title:
    st.title("모비딕 테니스")
    st.caption("대회 관리 & 순위 시스템")

tournaments = db.get_tournaments()
# 대회 목록: 대회 날짜 최신순 (날짜 없음은 맨 아래, 동일 날짜·무일자는 생성일 최신순)
tournaments = sorted(
    tournaments,
    key=lambda t: t.get("created_at") or "",
    reverse=True,
)
tournaments = sorted(
    tournaments,
    key=lambda t: str(t.get("date") or "0000-01-01"),
    reverse=True,
)

logged_in = auth.is_logged_in()

# ── 시즌 전체 랭킹 ────────────────────────────────────────────────────────────
st.header("시즌 전체 랭킹")

if not tournaments:
    st.info("아직 대회가 없습니다.")
else:
    def get_year(t):
        if t.get("date"):
            return str(t["date"])[:4]
        return "날짜 미설정"

    years = sorted({get_year(t) for t in tournaments}, reverse=True)
    selected_year = st.selectbox("연도 선택", ["전체"] + years, index=0)

    selected_tournaments = tournaments if selected_year == "전체" else [
        t for t in tournaments if get_year(t) == selected_year
    ]

    # 시즌 랭킹은 승인된 대회만 반영
    approved_tournaments = [t for t in selected_tournaments if t.get("is_approved")]

    if not selected_tournaments:
        st.info(f"{selected_year}년에 해당하는 대회가 없습니다.")
    elif not approved_tournaments:
        st.info("승인된 대회가 없습니다. 관리자의 승인 후 랭킹에 반영됩니다.")
    else:
        standings_map = {}
        for t in approved_tournaments:
            tid = t["id"]
            if t.get("is_legacy"):
                legacy = db.get_legacy_results(tid)
                standings_map[tid] = [
                    {"name": r["player_name"], "rank": r["rank"]}
                    for r in legacy
                ]
            else:
                players = db.get_tournament_players(tid)
                if players:
                    standings_map[tid] = calculate_standings(
                        players,
                        db.get_matches(tid),
                        db.get_scoring_config(tid),
                        db.get_extra_scores(tid),
                    )

        season_ranking = get_season_ranking(approved_tournaments, standings_map)

        if not season_ranking:
            st.info("아직 순위 포인트를 얻은 선수가 없습니다. (각 대회 1~3위를 달성해야 부여)")
        else:
            rows = []
            for r in season_ranking:
                detail = r["detail"]
                gold   = sum(1 for info in detail.values() if info["rank"] == 1)
                silver = sum(1 for info in detail.values() if info["rank"] == 2)
                bronze = sum(1 for info in detail.values() if info["rank"] == 3)
                rows.append({
                    "시즌순위": r["rank"],
                    "이름": r["name"],
                    "랭킹포인트": r["points"],
                    "🥇": gold,
                    "🥈": silver,
                    "🥉": bronze,
                })

            df = pd.DataFrame(rows)

            def highlight_top3(row):
                colors = {1: "background-color: #FFD700", 2: "background-color: #C0C0C0", 3: "background-color: #CD7F32"}
                return [colors.get(row["시즌순위"], "")] * len(row)

            st.dataframe(df.style.apply(highlight_top3, axis=1), use_container_width=True, hide_index=True)
            st.caption("랭킹 포인트: 1위=3점 / 2위=2점 / 3위=1점 / 4위 이하=미부여")

st.divider()

# ── 대회 목록 ─────────────────────────────────────────────────────────────────
st.header("대회 목록")

col_main, col_form = st.columns([3, 2])

with col_main:
    if not tournaments:
        st.info("대회가 없습니다.")
    else:
        with st.expander(f"대회 목록 ({len(tournaments)}개)", expanded=True):
            page_t, paged_t = db.get_page_slice(tournaments, "dashboard_t_page")
            for t in page_t:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
                    with c1:
                        if t.get("is_approved"):
                            status = "🏆 승인"
                        elif t["is_finished"]:
                            status = "✅ 완료"
                        else:
                            status = "🔄 진행 중"
                        legacy_badge = " &nbsp; `레거시`" if t.get("is_legacy") else ""
                        st.markdown(f"**{t['name']}** &nbsp; {status}{legacy_badge}")
                        if t.get("date"):
                            st.caption(f"날짜: {t['date']}")
                        if t.get("description"):
                            st.caption(t["description"])
                    with c2:
                        if t.get("is_legacy"):
                            results = db.get_legacy_results(t["id"])
                            st.caption(f"순위 기록: {len(results)}/3")
                        else:
                            players_count = len(db.get_tournament_players(t["id"]))
                            matches_count = len(db.get_matches(t["id"]))
                            st.caption(f"선수 {players_count}명 / 경기 {matches_count}개")
                    with c3:
                        if logged_in:
                            label = "완료 취소" if t["is_finished"] else "완료 처리"
                            if t.get("is_approved"):
                                # 승인된 대회는 완료 처리/취소 모두 불가
                                st.button(label, key=f"finish_{t['id']}", disabled=True,
                                          help="승인된 대회는 수정할 수 없습니다. 운영 → 대회 승인에서 승인을 취소한 뒤 변경해 주세요.")
                            else:
                                if st.button(label, key=f"finish_{t['id']}"):
                                    db.finish_tournament(t["id"], not t["is_finished"])
                                    st.rerun()
                    with c4:
                        if logged_in:
                            if t.get("is_approved"):
                                # 승인된 대회는 삭제 불가 — 운영 탭에서 승인 취소 후 삭제
                                st.button("삭제", key=f"del_t_{t['id']}", disabled=True,
                                          help="승인된 대회는 삭제할 수 없습니다. 운영 → 대회 승인에서 승인을 취소한 뒤 삭제해 주세요.")
                            else:
                                if st.button("삭제", key=f"del_t_{t['id']}"):
                                    if st.session_state.get(f"confirm_del_{t['id']}"):
                                        db.delete_tournament(t["id"])
                                        st.rerun()
                                    else:
                                        st.session_state[f"confirm_del_{t['id']}"] = True
                                        st.warning("한 번 더 누르면 삭제됩니다.")
            if paged_t:
                db.render_page_nav(tournaments, "dashboard_t_page")

with col_form:
    if logged_in:
        st.subheader("새 대회 만들기")
        with st.form("create_tournament", clear_on_submit=True):
            name = st.text_input("대회 이름", placeholder="예: 2026 상반기 리그")
            date = st.date_input("대회 날짜 (선택)")
            desc = st.text_area("메모 (선택)", height=60)
            is_legacy = st.checkbox("레거시 대회", help="대진표·경기 없이 1~3위만 기록하는 과거 대회용 모드")

            if st.form_submit_button("대회 생성"):
                if not name.strip():
                    st.error("대회 이름을 입력해 주세요.")
                else:
                    db.create_tournament(name.strip(), str(date), desc.strip(), is_legacy)
                    st.success(f"'{name}' 대회를 만들었습니다!")
                    st.rerun()
    else:
        st.info("대회를 생성하거나 관리하려면 로그인이 필요합니다.")
