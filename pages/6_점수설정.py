"""
점수 설정 페이지
- 프리셋 선택으로 빠르게 계산 방식 변경
- 항목별 ON/OFF + 점수값 직접 수정
"""
import streamlit as st
import db
from logic.scoring import PRESETS, apply_preset

st.set_page_config(page_title="점수 설정", page_icon="⚙️")
st.title("점수 설정")

# ── 사이드바: 대회 선택 ───────────────────────────────────────────────────────
tournaments = db.get_tournaments()
if not tournaments:
    st.warning("먼저 홈에서 대회를 만들어 주세요.")
    st.stop()

t_names = [t["name"] for t in tournaments]
selected_name = st.sidebar.selectbox("대회 선택", t_names)
tournament = next(t for t in tournaments if t["name"] == selected_name)
tid = tournament["id"]

st.caption(f"현재 대회: **{selected_name}** — 설정은 이 대회에만 적용됩니다.")

# ── 현재 설정 로드 ────────────────────────────────────────────────────────────
config = db.get_scoring_config(tid)

# ── 프리셋 선택 ───────────────────────────────────────────────────────────────
st.subheader("프리셋으로 빠르게 변경")
preset_names = list(PRESETS.keys())
selected_preset = st.selectbox("프리셋 선택", ["(직접 설정)"] + preset_names)

if selected_preset != "(직접 설정)":
    if st.button(f"'{selected_preset}' 프리셋 적용"):
        preset_values = apply_preset(selected_preset)
        for key, (is_active, score_value) in preset_values.items():
            if key in config:
                db.update_scoring_config(config[key]["id"], is_active, score_value)
        st.success(f"프리셋 '{selected_preset}' 적용 완료!")
        st.rerun()

st.divider()

# ── 항목별 세부 설정 ──────────────────────────────────────────────────────────
st.subheader("항목별 세부 설정")
st.caption("프리셋 적용 후 수치를 직접 조정할 수 있습니다. 변경 후 저장 버튼을 눌러주세요.")

# 입력 폼
with st.form("scoring_form"):
    new_values: dict[str, tuple] = {}

    for key, row in config.items():
        col1, col2, col3 = st.columns([3, 1, 2])
        with col1:
            st.markdown(f"**{row['label']}**")
        with col2:
            is_active = st.checkbox(
                "활성화",
                value=row["is_active"],
                key=f"active_{key}",
                label_visibility="collapsed",
            )
        with col3:
            score_value = st.number_input(
                "점수값",
                min_value=-9999, max_value=9999,
                value=row["score_value"],
                key=f"val_{key}",
                label_visibility="collapsed",
            )
        new_values[key] = (is_active, score_value, row["id"])

    if st.form_submit_button("설정 저장"):
        for key, (is_active, score_value, config_id) in new_values.items():
            db.update_scoring_config(config_id, is_active, score_value)
        st.success("점수 설정을 저장했습니다.")
        st.rerun()

# ── 설정 미리보기 ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("현재 점수 계산 공식 미리보기")
config = db.get_scoring_config(tid)  # 저장 후 최신값 반영

parts = []
for key, row in config.items():
    if not row["is_active"]:
        continue
    if key == "win_bonus":
        parts.append(f"승리수 × {row['score_value']}")
    elif key == "play_bonus":
        parts.append(f"경기수 × {row['score_value']}")
    elif key == "score_diff":
        parts.append(f"득실차 × {row['score_value']}")
    elif key == "wc_self_bonus":
        parts.append(f"WC선수 보너스 {row['score_value']}점/경기")
    elif key == "wc_partner_bonus":
        parts.append(f"WC파트너 승리 시 {row['score_value']}점")
    elif key == "extra_score":
        parts.append("추가 점수")

if parts:
    st.code("총점 = " + " + ".join(parts), language=None)
else:
    st.warning("활성화된 항목이 없습니다.")
