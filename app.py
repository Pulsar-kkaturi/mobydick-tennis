"""
모비딕 테니스 - 앱 진입점
- st.navigation()으로 페이지 구조 및 접근 권한 제어
- 사이드바: 로그인/로그아웃 + 대회 선택
"""
import streamlit as st
import auth
import db

st.set_page_config(
    page_title="모비딕 테니스",
    page_icon="🎾",
    layout="wide",
)

# ── 사이드바: 로그인/로그아웃 ─────────────────────────────────────────────────
with st.sidebar:
    user = auth.get_user()

    if user:
        st.success(f"👤 {user.email}")
        if st.button("로그아웃", use_container_width=True):
            auth.logout()
            st.rerun()
    else:
        with st.expander("🔐 로그인", expanded=False):
            email = st.text_input("이메일", key="login_email")
            password = st.text_input("비밀번호", type="password", key="login_pw")
            if st.button("로그인", use_container_width=True):
                if auth.login(email, password):
                    st.rerun()
                else:
                    st.error("이메일 또는 비밀번호가 틀렸습니다.")

    st.divider()

    # 대회 선택 (모든 페이지에서 공유)
    tournaments = db.get_tournaments()
    if tournaments:
        t_names = [t["name"] for t in tournaments]

        # 이전에 선택한 대회 유지
        prev = st.session_state.get("selected_tournament_name")
        default_idx = t_names.index(prev) if prev in t_names else 0

        selected_name = st.selectbox("대회 선택", t_names, index=default_idx)
        st.session_state["selected_tournament_name"] = selected_name
        st.session_state["selected_tournament"] = next(
            t for t in tournaments if t["name"] == selected_name
        )
    else:
        st.session_state.pop("selected_tournament", None)
        st.caption("대회가 없습니다. 대시보드에서 생성해 주세요.")

# ── 페이지 정의 ───────────────────────────────────────────────────────────────
dashboard  = st.Page("pages/dashboard.py",   title="대시보드",  icon="🏠", default=True)
ranking    = st.Page("pages/4_순위표.py",    title="순위표",    icon="🏆")
stats      = st.Page("pages/5_통계.py",      title="통계",      icon="📊")

players    = st.Page("pages/1_선수관리.py",  title="선수관리",  icon="👥")
t_settings = st.Page("pages/6_대회설정.py", title="대회설정",  icon="⚙️")
bracket    = st.Page("pages/2_대진표.py",    title="대진표",    icon="📋")
match_in   = st.Page("pages/3_경기입력.py", title="경기입력",  icon="✏️")

admin_page = st.Page("pages/admin.py",       title="운영",      icon="🛡️")

# ── role에 따라 네비게이션 구성 ───────────────────────────────────────────────
role = auth.get_role()

if auth.is_admin():
    nav = st.navigation({
        "": [dashboard, ranking, stats],
        "관리": [players],
        "대회관리": [t_settings, bracket, match_in],
        "운영": [admin_page],
    })
elif auth.is_user():
    nav = st.navigation({
        "": [dashboard, ranking, stats],
        "관리": [players],
        "대회관리": [t_settings, bracket, match_in],
    })
else:
    # 게스트
    nav = st.navigation([dashboard, ranking, stats])

nav.run()
