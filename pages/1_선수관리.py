"""
선수 관리 페이지

- 선수등록: 전역 선수 풀 등록/삭제(관리자), 성별·스타일·이름 편집
- 대회별 선수 배정은「대회설정」>「선수 배정」탭
"""
import streamlit as st
import db
import auth

st.title("선수 관리")

is_admin = auth.is_admin()
st.subheader("선수등록")

if is_admin:
    st.caption("이름 등록/삭제는 관리자만 가능합니다. 성별·스타일은 유저도 편집 가능합니다.")
else:
    st.caption("성별·플레이 스타일을 편집할 수 있습니다. 이름 등록/삭제는 관리자만 가능합니다.")

all_players = db.get_all_players()
editing = st.session_state.get("editing_player")

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
                    if is_admin:
                        if st.button("삭제", key=f"del_p_{p['id']}"):
                            db.delete_global_player(p["id"])
                            st.session_state.pop("editing_player", None)
                            st.rerun()

        # 편집 중인 선수 행 바로 아래에 폼 (맨 아래가 아님)
        if editing and editing.get("id") == p["id"]:
            with st.container(border=True):
                st.markdown(f"**{editing['name']}** 정보 편집")

                with st.form(f"edit_player_info_form_{p['id']}"):
                    gender_options = ["(미설정)"] + db.GENDERS
                    style_options = ["(미설정)"] + db.PLAY_STYLES

                    current_gender = editing.get("gender") or "(미설정)"
                    current_style = editing.get("play_style") or "(미설정)"

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

                    if is_admin:
                        new_name = st.text_input("이름", value=editing["name"])

                    c1, c2 = st.columns(2)
                    with c1:
                        submitted_save = st.form_submit_button("저장")
                    with c2:
                        submitted_cancel = st.form_submit_button("취소")

                    if submitted_save:
                        if is_admin:
                            new_name_val = new_name.strip()
                            if new_name_val != editing["name"]:
                                db.upsert_global_player(new_name_val, player_id=editing["id"])
                        db.update_player_info(
                            editing["id"],
                            None if new_gender == "(미설정)" else new_gender,
                            None if new_style == "(미설정)" else new_style,
                        )
                        st.session_state.pop("editing_player", None)
                        st.success("저장했습니다.")
                        st.rerun()

                    if submitted_cancel:
                        st.session_state.pop("editing_player", None)
                        st.rerun()
else:
    st.info("등록된 선수가 없습니다.")

st.divider()

# ── 선수 추가 (관리자 전용) ───────────────────────────────────────────────────
if is_admin:
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
