"""
순위표 페이지
- 일반 대회: 경기 결과 기반 실시간 순위 계산 + 엑셀 내보내기
- 레거시 대회: 1~3위 선수를 선수 풀에서 직접 선택해서 기록
"""
import io
import streamlit as st
import pandas as pd
import db
from logic.scoring import calculate_standings

st.title("순위표")

tournament = db.render_tournament_selector()
if not tournament:
    st.stop()

selected_name = tournament["name"]
tid = tournament["id"]

# ════════════════════════════════════════════════════════════════════════════════
# 레거시 대회: 1~3위 직접 입력
# ════════════════════════════════════════════════════════════════════════════════
if tournament.get("is_legacy"):
    st.subheader(f"{selected_name} — 레거시 순위 기록")
    st.caption("과거 대회 결과를 1~3위만 기록합니다. 시즌 랭킹 포인트 산정에 반영됩니다.")

    # 완료/승인된 대회는 수정 잠금
    is_locked = tournament.get("is_finished") or tournament.get("is_approved")
    if is_locked:
        lock_reason = "승인된" if tournament.get("is_approved") else "완료 처리된"
        st.warning(f"🔒 {lock_reason} 대회입니다. 순위를 수정할 수 없습니다.")

    # 현재 기록 로드
    existing = {r["rank"]: r["player_name"] for r in db.get_legacy_results(tid)}

    if not is_locked:
        # 전체 선수 풀에서 선택
        all_players = db.get_all_players()
        player_names = ["(선택 안 함)"] + [p["name"] for p in all_players]

        with st.form("legacy_form"):
            st.markdown("**순위별 선수 선택**")
            rank_labels = {1: "🥇 1위", 2: "🥈 2위", 3: "🥉 3위"}
            selections = {}

            for rank, label in rank_labels.items():
                current = existing.get(rank, "(선택 안 함)")
                default_idx = player_names.index(current) if current in player_names else 0
                selections[rank] = st.selectbox(label, player_names, index=default_idx, key=f"legacy_rank_{rank}")

            if st.form_submit_button("저장"):
                for rank, name in selections.items():
                    if name == "(선택 안 함)":
                        db.clear_legacy_result(tid, rank)
                    else:
                        db.set_legacy_result(tid, rank, name)
                st.success("저장했습니다.")
                st.rerun()

    # 현재 기록 미리보기 (잠금 여부 무관하게 항상 표시)
    results = db.get_legacy_results(tid)
    if results:
        st.divider()
        st.markdown("**현재 기록**")
        for r in results:
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(r["rank"], "")
            st.write(f"{medal} {r['rank']}위 — **{r['player_name']}**")
    else:
        st.info("아직 기록된 순위가 없습니다.")

    st.stop()  # 레거시 대회는 여기서 종료

# ════════════════════════════════════════════════════════════════════════════════
# 일반 대회: 경기 결과 기반 순위 계산
# ════════════════════════════════════════════════════════════════════════════════
players = db.get_tournament_players(tid)
matches = db.get_matches(tid)
config = db.get_scoring_config(tid)
extra_scores = db.get_extra_scores(tid)

if not players:
    st.info("선수가 없습니다. 선수 관리 페이지에서 먼저 등록해 주세요.")
    st.stop()

standings = calculate_standings(players, matches, config, extra_scores)

st.subheader(f"{selected_name} 순위표")

rows = []
for s in standings:
    rows.append({
        "순위": s["rank"],
        "이름": s["name"],
        "승리수": s["wins"],
        "경기수": s["played"],
        "득실차": s["score_diff"],
        "WC보너스": s["wc_bonus"],
        "파트너보너스": s["partner_bonus"],
        "추가점수": s["extra"],
        "총점": s["total"],
    })

df = pd.DataFrame(rows)

def highlight_top3(row):
    colors = {1: "background-color: #FFD700", 2: "background-color: #C0C0C0", 3: "background-color: #CD7F32"}
    return [colors.get(row["순위"], "")] * len(row)

st.dataframe(
    df.style.apply(highlight_top3, axis=1),
    use_container_width=True,
    hide_index=True,
)

# ── 엑셀 내보내기 ─────────────────────────────────────────────────────────────
st.divider()
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="순위표")
buffer.seek(0)

st.download_button(
    label="엑셀로 내보내기",
    data=buffer,
    file_name=f"{selected_name}_순위표.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── 현재 점수 계산 방식 확인 ──────────────────────────────────────────────────
with st.expander("현재 점수 계산 방식 확인"):
    for key, row in config.items():
        status = "✅" if row["is_active"] else "❌"
        st.write(f"{status} **{row['label']}** : {row['score_value']}점")
