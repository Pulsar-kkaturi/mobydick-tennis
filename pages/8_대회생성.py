"""
대회 생성 페이지
- 새 대회 생성 전용
"""
import streamlit as st
import auth
import db

st.title("대회 생성")
st.caption("새 대회를 생성하고 대회 등급(Premier/Open)을 설정합니다.")

if not auth.is_logged_in():
    st.info("대회를 생성하려면 로그인이 필요합니다.")
    st.stop()

st.subheader("새 대회 만들기")
with st.form("create_tournament_manage", clear_on_submit=True):
    name = st.text_input("대회 이름", placeholder="예: 2026 상반기 리그")
    date = st.date_input("대회 날짜 (선택)")
    desc = st.text_area("메모 (선택)", height=60)
    tournament_type_label = st.selectbox("대회 등급", ["Premier", "Open"], index=1)
    is_legacy = st.checkbox("레거시 대회", help="대진표·경기 없이 1~3위만 기록하는 과거 대회용 모드")

    if st.form_submit_button("대회 생성", type="primary"):
        if not name.strip():
            st.error("대회 이름을 입력해 주세요.")
        else:
            tournament_type = "PREMIER" if tournament_type_label == "Premier" else "OPEN"
            db.create_tournament(
                name=name.strip(),
                date=str(date),
                description=desc.strip(),
                is_legacy=is_legacy,
                tournament_type=tournament_type,
            )
            st.success(f"'{name}' 대회를 만들었습니다!")
            st.rerun()
