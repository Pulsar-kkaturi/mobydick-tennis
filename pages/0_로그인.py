"""
로그인 / 회원가입 / 비밀번호 재설정 페이지

- 로그인 상태면 안내 후 리다이렉트
- 비로그인 상태: 탭으로 로그인 / 회원가입 / 비밀번호 재설정
"""
import datetime

import streamlit as st
import auth

LOGO_PATH = "Assets/LOGO_2026_HJA.png"

# 로그인 됐으면 이 페이지 볼 필요 없음
if auth.is_logged_in() and not auth.is_otp_reset_mode():
    st.info("이미 로그인되어 있습니다.")
    st.stop()

# ── 로고 ─────────────────────────────────────────────────────────────────────
col_l, col_c, col_r = st.columns([1, 1, 1])
with col_c:
    st.image(LOGO_PATH, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── OTP 비밀번호 재설정 단계 2·3: 인증 후 새 비밀번호 입력 ───────────────────
# (단계 1=이메일 입력은 탭에서, 2=OTP 입력, 3=새 비밀번호는 여기서 처리)
if auth.is_otp_reset_mode():
    st.subheader("새 비밀번호 설정")
    st.caption("OTP 인증이 완료되었습니다. 새 비밀번호를 입력해 주세요.")
    with st.form("new_pw_form"):
        npw = st.text_input("새 비밀번호", type="password", placeholder="영문+숫자 8자 이상")
        npw2 = st.text_input("새 비밀번호 확인", type="password")
        submitted = st.form_submit_button("비밀번호 변경", type="primary", use_container_width=True)
    if submitted:
        ok, msg = auth.submit_new_password(npw, npw2)
        if ok:
            st.success(msg + " 사이드바에서 로그인하거나 대시보드를 이용해 주세요.")
        else:
            st.error(msg)
    if st.button("취소"):
        st.session_state.pop("otp_reset_mode", None)
        st.rerun()
    st.stop()


# ── 탭: 로그인 / 회원가입 / 비밀번호 재설정 ──────────────────────────────────
tab_login, tab_signup, tab_reset = st.tabs(["로그인", "회원가입", "비밀번호 재설정"])

# ── 탭 1: 로그인 ─────────────────────────────────────────────────────────────
with tab_login:
    with st.form("login_form"):
        email = st.text_input("이메일", placeholder="가입 시 사용한 이메일")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)
    if submitted:
        if auth.login(email, password):
            st.rerun()
        else:
            st.error("이메일 또는 비밀번호가 틀렸습니다.")

# ── 탭 2: 회원가입 ───────────────────────────────────────────────────────────
with tab_signup:
    st.caption("영문+숫자 조합 8자 이상 비밀번호")
    with st.form("signup_form"):
        su_name = st.text_input("이름")
        su_email = st.text_input("이메일 (로그인 ID)")
        su_pw = st.text_input("비밀번호", type="password")
        su_pw2 = st.text_input("비밀번호 확인", type="password")
        su_birth = st.date_input(
            "생년월일",
            min_value=datetime.date(1920, 1, 1),
            max_value=datetime.date.today(),
            value=None,
        )
        signup_submitted = st.form_submit_button("회원가입", type="primary", use_container_width=True)

    if signup_submitted:
        if su_pw != su_pw2:
            st.error("비밀번호 확인이 일치하지 않습니다.")
        else:
            ok, msg = auth.signup(su_name, su_email, su_pw, su_birth)
            if ok:
                st.session_state["signup_popup_payload"] = {
                    "name": su_name.strip(),
                    "email": su_email.strip(),
                    "detail": msg,
                }
                st.rerun()
            else:
                st.error(msg)

# ── 탭 3: 비밀번호 재설정 (OTP) ─────────────────────────────────────────────
with tab_reset:
    # 단계 관리: otp_reset_email 이 없으면 1단계, 있으면 2단계
    otp_email = st.session_state.get("otp_reset_email", "")

    if not otp_email:
        # 단계 1: 이메일 입력 → OTP 발송
        st.caption("가입 시 사용한 이메일을 입력하면 6자리 인증 코드를 보내 드립니다.")
        with st.form("otp_send_form"):
            r_email = st.text_input("이메일")
            send_submitted = st.form_submit_button("인증 코드 받기", type="primary", use_container_width=True)
        if send_submitted:
            ok, msg = auth.send_reset_otp(r_email)
            if ok:
                st.session_state["otp_reset_email"] = r_email.strip()
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    else:
        # 단계 2: 6자리 코드 입력 → 검증
        st.caption(f"**{otp_email}** 로 보낸 6자리 코드를 입력해 주세요.")
        st.caption("코드는 수 분 내에 만료됩니다. 스팸함도 확인해 주세요.")
        with st.form("otp_verify_form"):
            otp_code = st.text_input("6자리 인증 코드", max_chars=6, placeholder="123456")
            verify_submitted = st.form_submit_button("확인", type="primary", use_container_width=True)
        if verify_submitted:
            ok, msg = auth.verify_reset_otp(otp_email, otp_code)
            if ok:
                # otp_reset_mode 가 켜졌으므로 이 페이지 상단에서 새 비밀번호 폼으로 이동
                st.session_state.pop("otp_reset_email", None)
                st.rerun()
            else:
                st.error(msg)

        # 이메일 다시 입력 or 재발송
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("코드 재발송", use_container_width=True):
                ok, msg = auth.send_reset_otp(otp_email)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
        with col_b:
            if st.button("이메일 다시 입력", use_container_width=True):
                st.session_state.pop("otp_reset_email", None)
                st.rerun()
