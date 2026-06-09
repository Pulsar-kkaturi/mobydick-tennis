"""
대시보드 페이지 (메인 홈)
- 시즌 전체 랭킹 (연도 필터)
- 대회 목록 및 생성/삭제 (로그인 시 관리 기능 활성화)
"""
import streamlit as st
import pandas as pd
from datetime import date
import db
import auth
from logic.scoring import calculate_standings, get_season_ranking

def get_default_year_index(year_options: list[str]) -> int:
    """['전체', '2026', ...] 형태 옵션에서 기본 인덱스를 반환."""
    target_year = str(date.today().year)
    return year_options.index(target_year) if target_year in year_options else 0


col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("Assets/LOGO_2026_HJA.png", width=90)
with col_title:
    st.title("MOTIS")
    st.markdown(
        """
        <p style="margin: 0; color: #111111; font-size: 1.40rem; font-weight: 600;">
          Mobydick Open Tournament Information System<br> 
          (모비딕테니스 대회 & 랭킹 관리 시스템)
        </p>
        <p style="margin-top: 0.35rem; color: #7A7A7A; font-size: 0.95rem;">
          version 1.01 (last updated: 2026.06.09)
        </p>
        """,
        unsafe_allow_html=True,
    )

tournaments = db.get_tournaments()  # 날짜 최신순은 get_tournaments()에서 통일

logged_in = auth.is_logged_in()


def get_year(t):
    if t.get("date"):
        return str(t["date"])[:4]
    return "날짜 미설정"


def build_tournament_podium(t):
    """대회별 1/2/3위 선수 목록 반환."""
    tid = t["id"]
    podium = {1: [], 2: [], 3: []}
    if t.get("is_legacy"):
        legacy = db.get_legacy_results(tid)
        for row in legacy:
            rank = row.get("rank")
            if rank in podium:
                podium[rank].append(row["player_name"])
        return podium

    players = db.get_tournament_players(tid)
    if not players:
        return podium
    standings = calculate_standings(
        players,
        db.get_matches(tid),
        db.get_scoring_config(tid),
        db.get_extra_scores(tid),
    )
    for row in standings:
        rank = row.get("rank")
        if rank in podium:
            podium[rank].append(row["name"])
    return podium

# ── 시즌 전체 랭킹 ────────────────────────────────────────────────────────────
st.header("시즌 전체 랭킹")

if not tournaments:
    st.info("아직 대회가 없습니다.")
else:
    years = sorted({get_year(t) for t in tournaments}, reverse=True)
    season_year_options = ["전체"] + years
    selected_year = st.selectbox(
        "연도 선택",
        season_year_options,
        index=get_default_year_index(season_year_options),
        key="season_year_select",
    )

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
                p_gold = sum(1 for info in detail.values() if info["rank"] == 1 and info.get("type") == "PREMIER")
                p_silver = sum(1 for info in detail.values() if info["rank"] == 2 and info.get("type") == "PREMIER")
                p_bronze = sum(1 for info in detail.values() if info["rank"] == 3 and info.get("type") == "PREMIER")
                o_gold = sum(1 for info in detail.values() if info["rank"] == 1 and info.get("type") == "OPEN")
                o_silver = sum(1 for info in detail.values() if info["rank"] == 2 and info.get("type") == "OPEN")
                o_bronze = sum(1 for info in detail.values() if info["rank"] == 3 and info.get("type") == "OPEN")
                rows.append({
                    "시즌순위": r["rank"],
                    "이름": r["name"],
                    "랭킹포인트": r["points"],
                    "Premier🥇": p_gold,
                    "Premier🥈": p_silver,
                    "Premier🥉": p_bronze,
                    "Open🥇": o_gold,
                    "Open🥈": o_silver,
                    "Open🥉": o_bronze,
                })

            with st.expander(f"시즌 랭킹 ({len(rows)}명)", expanded=True):
                page_rows, paged_sr = db.get_page_slice(rows, "season_ranking_page")
                df = pd.DataFrame(page_rows)

                def highlight_top3(row):
                    colors = {1: "background-color: #FFD700", 2: "background-color: #C0C0C0", 3: "background-color: #CD7F32"}
                    return [colors.get(row["시즌순위"], "")] * len(row)

                st.dataframe(df.style.apply(highlight_top3, axis=1), use_container_width=True, hide_index=True)
                if paged_sr:
                    db.render_page_nav(rows, "season_ranking_page")

            st.caption("랭킹 포인트: Premier(1위=5점, 2위=3점, 3위=2점) / Open(1위=3점, 2위=2점, 3위=1점) / 4위 이하=미부여")

st.divider()

# ── 대회 목록 ─────────────────────────────────────────────────────────────────
st.header("대회 목록")
if not tournaments:
    st.info("대회가 없습니다.")
else:
    list_years = sorted({get_year(t) for t in tournaments}, reverse=True)
    list_year_options = ["전체"] + list_years
    list_selected_year = st.selectbox(
        "대회 목록 연도 선택",
        list_year_options,
        index=get_default_year_index(list_year_options),
        key="list_year_select",
    )
    list_tournaments = tournaments if list_selected_year == "전체" else [
        t for t in tournaments if get_year(t) == list_selected_year
    ]

    if not list_tournaments:
        st.info(f"{list_selected_year}년에 해당하는 대회가 없습니다.")
    else:
        with st.expander(f"대회 목록 ({len(list_tournaments)}개)", expanded=True):
            page_t, paged_t = db.get_page_slice(list_tournaments, "dashboard_t_page")
            for t in page_t:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([4, 2.3, 2.3, 1, 1])
                    with c1:
                        if t.get("is_approved"):
                            status = "🏆 승인"
                        elif t["is_finished"]:
                            status = "✅ 완료"
                        else:
                            status = "🔄 진행 중"
                        legacy_badge = " &nbsp; `레거시`" if t.get("is_legacy") else ""
                        t_type = (t.get("tournament_type") or "OPEN").upper()
                        type_badge = "`Premier`" if t_type == "PREMIER" else "`Open`"
                        st.markdown(f"**{t['name']}** &nbsp; {status} &nbsp; {type_badge}{legacy_badge}")
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
                        podium = build_tournament_podium(t)
                        rank1 = ", ".join(podium[1]) if podium[1] else "—"
                        st.caption(f"🥇 1위: {rank1}")
                    with c4:
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
                    with c5:
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
                db.render_page_nav(list_tournaments, "dashboard_t_page")
