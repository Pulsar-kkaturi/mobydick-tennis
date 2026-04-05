"""
선수 관리 페이지

탭 구성:
1. 전체 선수 풀
   - 선수 등록/삭제: 관리자만
   - 성별/플레이 스타일 편집: 유저도 가능
2. 대회별 배정: 유저도 가능
"""
import streamlit as st
import db
import auth

st.title("선수 관리")

is_admin = auth.is_admin()
tab_pool, tab_assign = st.tabs(["전체 선수 풀", "대회별 배정"])


# ════════════════════════════════════════════════════════════════════════════════
# 탭 1: 전체 선수 풀
# ════════════════════════════════════════════════════════════════════════════════
with tab_pool:
    st.subheader("전체 선수 풀")

    if is_admin:
        st.caption("이름 등록/삭제는 관리자만 가능합니다. 성별·스타일은 유저도 편집 가능합니다.")
    else:
        st.caption("성별·플레이 스타일을 편집할 수 있습니다. 이름 등록/삭제는 관리자만 가능합니다.")

    all_players = db.get_all_players()

    if all_players:
        for p in all_players:
            with st.container(border=True):
                col_name, col_gender, col_style, col_btns = st.columns([2, 1, 2, 2])

                with col_name:
                    st.markdown(f"**{p['name']}**")

                with col_gender:
                    st.caption(p.get("gender") or "성별 미설정")

                with col_style:
                    st.caption(p.get("play_style") or "스타일 미설정")

                with col_btns:
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("편집", key=f"edit_p_{p['id']}"):
                            st.session_state["editing_player"] = p
                    with btn_col2:
                        # 삭제는 관리자만
                        if is_admin:
                            if st.button("삭제", key=f"del_p_{p['id']}"):
                                db.delete_global_player(p["id"])
                                st.rerun()
    else:
        st.info("등록된 선수가 없습니다.")

    st.divider()

    # ── 선수 편집 폼 ─────────────────────────────────────────────────────────
    editing = st.session_state.get("editing_player")
    if editing:
        st.subheader(f"**{editing['name']}** 정보 편집")

        with st.form("edit_player_info_form"):
            gender_options = ["(미설정)"] + db.GENDERS
            style_options  = ["(미설정)"] + db.PLAY_STYLES

            current_gender = editing.get("gender") or "(미설정)"
            current_style  = editing.get("play_style") or "(미설정)"

            new_gender = st.selectbox(
                "성별",
                gender_options,
                index=gender_options.index(current_gender) if current_gender in gender_options else 0,
            )
            new_style = st.selectbox(
                "플레이 스타일",
                style_options,
                index=style_options.index(current_style) if current_style in style_options else 0,
            )

            # 관리자는 이름도 수정 가능
            if is_admin:
                new_name = st.text_input("이름", value=editing["name"])
            
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("저장"):
                    if is_admin:
                        if new_name.strip() != editing["name"]:
                            db.upsert_global_player(new_name.strip(), player_id=editing["id"])
                    db.update_player_info(
                        editing["id"],
                        None if new_gender == "(미설정)" else new_gender,
                        None if new_style == "(미설정)" else new_style,
                    )
                    st.session_state.pop("editing_player", None)
                    st.success("저장했습니다.")
                    st.rerun()
            with c2:
                if st.form_submit_button("취소"):
                    st.session_state.pop("editing_player", None)
                    st.rerun()

    # ── 선수 추가 (관리자 전용) ───────────────────────────────────────────────
    if is_admin:
        st.divider()
        st.subheader("선수 추가")
        with st.form("add_player_form", clear_on_submit=True):
            new_name = st.text_input("이름")
            if st.form_submit_button("추가"):
                if not new_name.strip():
                    st.error("이름을 입력해 주세요.")
                else:
                    db.upsert_global_player(new_name.strip())
                    st.success(f"'{new_name}' 추가 완료!")
                    st.rerun()
    else:
        st.info("선수 등록 및 삭제는 관리자만 가능합니다.")


# ════════════════════════════════════════════════════════════════════════════════
# 탭 2: 대회별 선수 배정 (유저도 가능)
# ════════════════════════════════════════════════════════════════════════════════
with tab_assign:
    st.subheader("대회별 선수 배정")

    tournament = st.session_state.get("selected_tournament")
    if not tournament:
        st.warning("사이드바에서 대회를 선택해 주세요.")
        st.stop()

    selected_name = tournament["name"]
    tid = tournament["id"]
    st.caption(f"현재 대회: **{selected_name}**")

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
                # 선수 풀에서 성별/스타일 표시
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
                        st.rerun()
    else:
        st.info("아직 배정된 선수가 없습니다.")

    # 배정 선수 수정 폼
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

    # 선수 풀에서 배정
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
