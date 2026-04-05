"""
대회설정 페이지

탭:
- 선수 배정: 대회에 선수 풀에서 배정·직함·WC (기존 선수관리의 대회별 배정)
- 점수 설정: 프리셋·항목별 점수
"""
import streamlit as st
import db
from logic.scoring import PRESETS, apply_preset

st.title("대회설정")

tournament = st.session_state.get("selected_tournament")
if not tournament:
    st.warning("사이드바에서 대회를 선택해 주세요.")
    st.stop()

selected_name = tournament["name"]
tid = tournament["id"]

st.caption(f"현재 대회: **{selected_name}** — 설정은 이 대회에만 적용됩니다.")

tab_assign, tab_score = st.tabs(["선수 배정", "점수 설정"])


# ════════════════════════════════════════════════════════════════════════════════
# 탭 1: 선수 배정
# ════════════════════════════════════════════════════════════════════════════════
with tab_assign:
    st.subheader("선수 배정")

    assigned = db.get_tournament_players(tid)
    assigned_player_ids = {p["player_id"] for p in assigned}

    st.markdown(f"**{selected_name}** 배정 선수 ({len(assigned)}명)")

    if assigned:
        for p in assigned:
            col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 1])
            with col1:
                st.write(f"**{p['name']}**")
            with col2:
                st.caption(p.get("title") or "-")
            with col3:
                player_info = next((pl for pl in db.get_all_players() if pl["id"] == p["player_id"]), {})
                info_str = " | ".join(filter(None, [player_info.get("gender"), player_info.get("play_style")]))
                st.caption(info_str or "-")
            with col4:
                st.caption("🃏 WC" if p["is_wildcard"] else "")
            with col5:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("수정", key=f"edit_tp_{p['id']}"):
                        st.session_state["editing_tp"] = p
                with c2:
                    if st.button("제거", key=f"rem_tp_{p['id']}"):
                        db.remove_player_from_tournament(p["id"])
                        st.session_state.pop("editing_tp", None)
                        st.rerun()
    else:
        st.info("아직 배정된 선수가 없습니다.")

    editing_tp = st.session_state.get("editing_tp")
    if editing_tp:
        st.divider()
        st.markdown(f"**{editing_tp['name']}** 배정 정보 수정")
        with st.form("edit_tp_form"):
            new_title = st.text_input("직함", value=editing_tp.get("title") or "")
            new_wc = st.checkbox("와일드카드", value=editing_tp["is_wildcard"])
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("저장"):
                    db.update_tournament_player(editing_tp["id"], new_title.strip(), new_wc)
                    st.session_state.pop("editing_tp", None)
                    st.success("수정했습니다.")
                    st.rerun()
            with c2:
                if st.form_submit_button("취소"):
                    st.session_state.pop("editing_tp", None)
                    st.rerun()

    st.divider()

    st.markdown("**선수 풀에서 배정 추가**")
    all_players = db.get_all_players()
    available = [p for p in all_players if p["id"] not in assigned_player_ids]

    if not available:
        st.info("전체 풀의 모든 선수가 이미 배정되어 있습니다.")
    else:
        with st.form("assign_player_form", clear_on_submit=True):
            selected_players = st.multiselect(
                "추가할 선수 선택",
                options=[p["name"] for p in available],
            )
            title_input = st.text_input("직함 (선택사항, 공통 적용)")
            wc_input = st.checkbox("와일드카드")

            if st.form_submit_button("배정"):
                if not selected_players:
                    st.error("선수를 1명 이상 선택해 주세요.")
                else:
                    name_to_id = {p["name"]: p["id"] for p in available}
                    for name in selected_players:
                        db.add_player_to_tournament(tid, name_to_id[name], title_input.strip(), wc_input)
                    st.success(f"{len(selected_players)}명 배정 완료!")
                    st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# 탭 2: 점수 설정
# ════════════════════════════════════════════════════════════════════════════════
with tab_score:
    st.subheader("점수 설정")

    config = db.get_scoring_config(tid)

    st.markdown("##### 프리셋으로 빠르게 변경")
    preset_names = list(PRESETS.keys())
    selected_preset = st.selectbox("프리셋 선택", ["(직접 설정)"] + preset_names, key="preset_pick")

    if selected_preset != "(직접 설정)":
        if st.button(f"'{selected_preset}' 프리셋 적용", key="apply_preset_btn"):
            preset_values = apply_preset(selected_preset)
            for key, (is_active, score_value) in preset_values.items():
                if key in config:
                    db.update_scoring_config(config[key]["id"], is_active, score_value)
            st.success(f"프리셋 '{selected_preset}' 적용 완료!")
            st.rerun()

    st.divider()

    st.markdown("##### 항목별 세부 설정")
    st.caption("프리셋 적용 후 수치를 직접 조정할 수 있습니다. 변경 후 저장 버튼을 눌러주세요.")

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
                    min_value=-9999,
                    max_value=9999,
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

    st.divider()
    st.markdown("##### 현재 점수 계산 공식 미리보기")
    config = db.get_scoring_config(tid)

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
