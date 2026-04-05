"""
내 정보 페이지 (로그인 상태 전용)

- 이름·이메일·생년월일 조회
- 이름·생년월일 수정
- 비밀번호 변경 (현재 비밀번호 확인 후)
"""
import datetime

import streamlit as st
import auth

# 로그인 확인
if not auth.is_logged_in():
    st.warning("로그인이 필요합니다.")
    if st.button("로그인 페이지로"):
        st.switch_page("pages/0_로그인.py")
    st.stop()

st.title("내 정보")

profile = auth.get_my_profile()
user = auth.get_user()

# ── 현재 정보 표시 ────────────────────────────────────────────────────────────
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**이름**")
        st.write(profile.get("full_name") or "(미설정)")
        st.markdown("**생년월일**")
        st.write(profile.get("birth_date") or "(미설정)")
    with col2:
        st.markdown("**이메일 (로그인 ID)**")
        st.write(profile.get("email") or (user.email if user else "(알 수 없음)"))
        st.markdown("**역할**")
        role_labels = {"master": "👑 마스터", "admin": "🛡️ 관리자", "user": "👤 유저"}
        st.write(role_labels.get(profile.get("role", ""), profile.get("role", "-")))

st.divider()

# ── 정보 수정 ─────────────────────────────────────────────────────────────────
st.subheader("정보 수정")

with st.form("edit_profile_form"):
    new_name = st.text_input("이름", value=profile.get("full_name") or "")

    # birth_date 문자열 → date 객체로 변환
    bd_str = profile.get("birth_date")
    try:
        bd_default = datetime.date.fromisoformat(bd_str) if bd_str else None
    except ValueError:
        bd_default = None

    new_birth = st.date_input(
        "생년월일",
        value=bd_default,
        min_value=datetime.date(1920, 1, 1),
        max_value=datetime.date.today(),
    )
    if st.form_submit_button("저장", type="primary"):
        ok, msg = auth.update_my_profile(new_name, new_birth)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

st.divider()

# ── 비밀번호 변경 ─────────────────────────────────────────────────────────────
st.subheader("비밀번호 변경")
st.caption("현재 비밀번호를 먼저 입력해 주세요.")

with st.form("change_pw_form"):
    cur_pw = st.text_input("현재 비밀번호", type="password")
    new_pw = st.text_input("새 비밀번호", type="password", placeholder="영문+숫자 8자 이상")
    new_pw2 = st.text_input("새 비밀번호 확인", type="password")
    if st.form_submit_button("비밀번호 변경", type="primary"):
        ok, msg = auth.change_password(cur_pw, new_pw, new_pw2)
        if ok:
            st.success(msg)
        else:
            st.error(msg)
