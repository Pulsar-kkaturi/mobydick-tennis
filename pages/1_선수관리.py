"""
선수 관리 페이지

두 섹션으로 구성:
1. 전체 선수 풀 — 이름 등록/수정/삭제 (대회 무관)
2. 대회별 배정 — 풀에서 선수를 골라 직함·와일드카드 설정
"""
import streamlit as st
import db

st.set_page_config(page_title="선수 관리", page_icon="🎾")
st.title("선수 관리")

# ── 탭 구분 ───────────────────────────────────────────────────────────────────
tab_pool, tab_assign = st.tabs(["전체 선수 풀", "대회별 배정"])


# ════════════════════════════════════════════════════════════════════════════════
# 탭 1: 전체 선수 풀 관리
# ════════════════════════════════════════════════════════════════════════════════
with tab_pool:
    st.subheader("전체 선수 풀")
    st.caption("여기서 등록한 선수는 모든 대회에서 불러와 배정할 수 있습니다.")

    all_players = db.get_all_players()

    if all_players:
        for p in all_players:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.write(p["name"])
            with col2:
                if st.button("수정", key=f"edit_p_{p['id']}"):
                    st.session_state["editing_global_player"] = p
            with col3:
                if st.button("삭제", key=f"del_p_{p['id']}"):
                    db.delete_global_player(p["id"])
                    st.rerun()
    else:
        st.info("등록된 선수가 없습니다.")

    st.divider()

    # 선수 추가 / 수정 폼
    editing = st.session_state.get("editing_global_player")
    st.subheader("선수 수정" if editing else "선수 추가")

    with st.form("global_player_form", clear_on_submit=True):
        name = st.text_input("이름", value=editing["name"] if editing else "")
        if st.form_submit_button("저장"):
            if not name.strip():
                st.error("이름을 입력해 주세요.")
            else:
                db.upsert_global_player(name.strip(), player_id=editing["id"] if editing else None)
                st.session_state.pop("editing_global_player", None)
                st.success("저장했습니다.")
                st.rerun()

    if editing and st.button("취소"):
        st.session_state.pop("editing_global_player", None)
        st.rerun()



# ════════════════════════════════════════════════════════════════════════════════
# 탭 2: 대회별 선수 배정
# ════════════════════════════════════════════════════════════════════════════════
with tab_assign:
    st.subheader("대회별 선수 배정")

    tournaments = db.get_tournaments()
    if not tournaments:
        st.warning("먼저 홈에서 대회를 만들어 주세요.")
        st.stop()

    t_names = [t["name"] for t in tournaments]
    selected_name = st.selectbox("대회 선택", t_names)
    tournament = next(t for t in tournaments if t["name"] == selected_name)
    tid = tournament["id"]

    # 현재 이 대회에 배정된 선수
    assigned = db.get_tournament_players(tid)
    assigned_player_ids = {p["player_id"] for p in assigned}

    # 배정된 선수 목록
    st.markdown(f"**{selected_name}** 배정 선수 ({len(assigned)}명)")

    if assigned:
        for p in assigned:
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                st.write(f"**{p['name']}**")
            with col2:
                st.caption(p.get("title") or "-")
            with col3:
                st.caption("🃏 WC" if p["is_wildcard"] else "")
            with col4:
                if st.button("수정", key=f"edit_tp_{p['id']}"):
                    st.session_state["editing_tp"] = p
                if st.button("제거", key=f"rem_tp_{p['id']}"):
                    db.remove_player_from_tournament(p["id"])
                    st.rerun()
    else:
        st.info("아직 배정된 선수가 없습니다.")

    # 배정된 선수 수정 폼
    editing_tp = st.session_state.get("editing_tp")
    if editing_tp:
        st.divider()
        st.markdown(f"**{editing_tp['name']}** 정보 수정")
        with st.form("edit_tp_form"):
            new_title = st.text_input("직함", value=editing_tp.get("title") or "")
            new_wc = st.checkbox("와일드카드", value=editing_tp["is_wildcard"])
            if st.form_submit_button("저장"):
                db.update_tournament_player(editing_tp["id"], new_title.strip(), new_wc)
                st.session_state.pop("editing_tp", None)
                st.success("수정했습니다.")
                st.rerun()
        if st.button("취소"):
            st.session_state.pop("editing_tp", None)
            st.rerun()

    st.divider()

    # 전체 풀에서 선수 추가
    st.markdown("**선수 풀에서 선택해서 추가**")
    all_players = db.get_all_players()
    # 아직 이 대회에 배정되지 않은 선수만 표시
    available = [p for p in all_players if p["id"] not in assigned_player_ids]

    if not available:
        st.info("전체 풀의 모든 선수가 이미 배정되어 있습니다.")
    else:
        with st.form("assign_player_form", clear_on_submit=True):
            selected_players = st.multiselect(
                "추가할 선수 선택",
                options=[p["name"] for p in available],
            )
            title_input = st.text_input("직함 (선택사항, 여러 명 선택 시 공통 적용)")
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
