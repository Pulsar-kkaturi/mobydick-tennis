"""
모비딕 테니스 - 앱 진입점
- st.navigation()으로 페이지 구조 및 접근 권한 제어
- 사이드바: 현재 로그인 계정 표시 + 로그인 페이지 링크 / 로그아웃
"""
import streamlit as st
import auth
import db

st.set_page_config(
    page_title="모비딕 테니스",
    page_icon="🎾",
    layout="wide",
)

# ── 회원가입 직후 안내 (한 번만 뜨는 다이얼로그) ───────────────────────────────
_popup = st.session_state.pop("signup_popup_payload", None)
if _popup:
    @st.dialog("회원가입 완료")
    def _signup_done_dialog():
        st.markdown(f"**{_popup['name']}** 님")
        st.markdown(f"`{_popup['email']}`")
        st.success("위 이메일로 가입이 완료되었습니다.")
        if _popup.get("detail"):
            st.caption(_popup["detail"])
        if st.button("확인", type="primary", use_container_width=True):
            st.rerun()

    _signup_done_dialog()

# ── 사이드바: 로그인 계정 표시 / 로그인 버튼 / 로그아웃 ───────────────────────
with st.sidebar:
    user = auth.get_user()

    if user:
        st.success(f"👤 {user.email}")
        if st.button("로그아웃", use_container_width=True):
            auth.logout()
            st.rerun()
    else:
        if st.button("🔐 로그인 / 회원가입", use_container_width=True, type="primary"):
            st.switch_page("pages/0_로그인.py")

    st.divider()

    # 대회 선택 (모든 페이지에서 공유)
    tournaments = db.get_tournaments()
    if tournaments:
        t_names = [t["name"] for t in tournaments]

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
login_page  = st.Page("pages/0_로그인.py",      title="로그인",    icon="🔐")
dashboard   = st.Page("pages/dashboard.py",     title="대시보드",  icon="🏠", default=True)
ranking     = st.Page("pages/4_순위표.py",      title="순위표",    icon="🏆")
stats       = st.Page("pages/5_통계.py",        title="통계",      icon="📊")

players     = st.Page("pages/1_선수관리.py",    title="선수관리",  icon="👥")
t_settings  = st.Page("pages/6_대회설정.py",   title="대회설정",  icon="⚙️")
bracket     = st.Page("pages/2_대진표.py",      title="대진표",    icon="📋")
match_in    = st.Page("pages/3_경기입력.py",    title="경기입력",  icon="✏️")

admin_page  = st.Page("pages/admin.py",         title="운영",      icon="🛡️")

# ── role에 따라 네비게이션 구성 ───────────────────────────────────────────────
if auth.is_admin():
    nav = st.navigation({
        "": [dashboard, ranking, stats],
        "관리": [players],
        "대회관리": [t_settings, bracket, match_in],
        "운영": [admin_page],
        "계정": [login_page],
    })
elif auth.is_user():
    nav = st.navigation({
        "": [dashboard, ranking, stats],
        "관리": [players],
        "대회관리": [t_settings, bracket, match_in],
        "계정": [login_page],
    })
else:
    # 게스트: 로그인 페이지 + 조회만
    nav = st.navigation({
        "": [dashboard, ranking, stats],
        "계정": [login_page],
    })

nav.run()
