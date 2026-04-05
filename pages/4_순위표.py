"""
순위표 페이지
- 대회별 실시간 순위 계산
- 엑셀 내보내기
"""
import io
import streamlit as st
import pandas as pd
import db
from logic.scoring import calculate_standings

st.set_page_config(page_title="순위표", page_icon="🏆")
st.title("순위표")

# ── 사이드바: 대회 선택 ───────────────────────────────────────────────────────
tournaments = db.get_tournaments()
if not tournaments:
    st.warning("먼저 홈에서 대회를 만들어 주세요.")
    st.stop()

t_names = [t["name"] for t in tournaments]
selected_name = st.sidebar.selectbox("대회 선택", t_names)
tournament = next(t for t in tournaments if t["name"] == selected_name)
tid = tournament["id"]

# ── 데이터 로드 ───────────────────────────────────────────────────────────────
players = db.get_players(tid)
matches = db.get_matches(tid)
config = db.get_scoring_config(tid)
extra_scores = db.get_extra_scores(tid)

if not players:
    st.info("선수가 없습니다. 선수 관리 페이지에서 먼저 등록해 주세요.")
    st.stop()

# ── 순위 계산 ─────────────────────────────────────────────────────────────────
standings = calculate_standings(players, matches, config, extra_scores)

# ── 표 출력 ───────────────────────────────────────────────────────────────────
st.subheader(f"{selected_name} 순위표")

# 활성화된 항목에 맞춰 표시 컬럼 동적 구성
col_labels = {
    "rank":            "순위",
    "name":            "이름",
    "wins":            "승리수",
    "played":          "경기수",
    "score_diff":      "득실차",
    "wc_bonus":        "WC보너스",
    "partner_bonus":   "파트너보너스",
    "extra":           "추가점수",
    "total":           "총점",
}

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

# 1위는 금색 배경 스타일
def highlight_top3(row):
    colors = {1: "background-color: #FFD700", 2: "background-color: #C0C0C0", 3: "background-color: #CD7F32"}
    color = colors.get(row["순위"], "")
    return [color] * len(row)

st.dataframe(
    df.style.apply(highlight_top3, axis=1),
    use_container_width=True,
    hide_index=True,
)

# ── 엑셀 내보내기 ─────────────────────────────────────────────────────────────
st.divider()
col1, col2 = st.columns([1, 3])
with col1:
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

# ── 상세 설정 정보 ────────────────────────────────────────────────────────────
with st.expander("현재 점수 계산 방식 확인"):
    for key, row in config.items():
        status = "✅" if row["is_active"] else "❌"
        st.write(f"{status} **{row['label']}** : {row['score_value']}점")
