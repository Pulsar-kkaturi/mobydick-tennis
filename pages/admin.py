"""
운영 페이지 (관리자 전용)
- 완료 처리된 대회 승인 → 시즌 랭킹 반영
- profiles 테이블에서 유저 role 관리
"""
import streamlit as st
import db
import auth

st.title("운영")

# 관리자 권한 재확인
if not auth.is_admin():
    st.error("관리자만 접근할 수 있습니다.")
    st.stop()

# ── 탭 구성 ───────────────────────────────────────────────────────────────────
tab_approval, tab_users = st.tabs(["대회 승인", "유저 관리"])


# ════════════════════════════════════════════════════════════════════════════════
# 탭 1: 대회 승인
# ════════════════════════════════════════════════════════════════════════════════
with tab_approval:
    st.subheader("대회 승인 관리")
    st.caption("완료 처리된 대회를 승인하면 시즌 랭킹에 반영됩니다.")

    tournaments = db.get_tournaments()

    if not tournaments:
        st.info("대회가 없습니다.")
    else:
        # 완료된 대회만 표시 (미완료 대회는 승인 대상 아님)
        finished = [t for t in tournaments if t["is_finished"]]
        unfinished = [t for t in tournaments if not t["is_finished"]]

        if unfinished:
            st.info(f"진행 중인 대회 {len(unfinished)}개는 완료 처리 후 승인할 수 있습니다.")

        if not finished:
            st.info("완료 처리된 대회가 없습니다.")
        else:
            for t in finished:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([4, 2, 2])
                    with c1:
                        legacy = " `레거시`" if t.get("is_legacy") else ""
                        st.markdown(f"**{t['name']}**{legacy}")
                        if t.get("date"):
                            st.caption(f"날짜: {t['date']}")
                    with c2:
                        if t["is_approved"]:
                            st.success("✅ 승인됨")
                        else:
                            st.warning("⏳ 승인 대기")
                    with c3:
                        if t["is_approved"]:
                            if st.button("승인 취소", key=f"unapprove_{t['id']}"):
                                db.approve_tournament(t["id"], False)
                                st.rerun()
                        else:
                            if st.button("승인", key=f"approve_{t['id']}", type="primary"):
                                db.approve_tournament(t["id"], True)
                                st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# 탭 2: 유저 관리
# ════════════════════════════════════════════════════════════════════════════════
with tab_users:
    st.subheader("유저 role 관리")
    st.caption("Supabase Auth에 등록된 사용자의 권한을 변경합니다.")

    client = db.get_client()
    # profiles 테이블 전체 조회
    profiles_res = client.table("profiles").select("id, role").execute()
    profiles = profiles_res.data

    if not profiles:
        st.info("등록된 유저가 없습니다.")
    else:
        # Supabase Admin API로 이메일 조회는 server-side에서만 가능하므로
        # user id와 role만 표시
        for p in profiles:
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.code(p["id"], language=None)
            with col2:
                badge = "🛡️ admin" if p["role"] == "admin" else "👤 user"
                st.write(badge)
            with col3:
                if p["role"] == "admin":
                    if st.button("일반유저로", key=f"demote_{p['id']}"):
                        client.table("profiles").update({"role": "user"}).eq("id", p["id"]).execute()
                        st.rerun()
                else:
                    if st.button("관리자로", key=f"promote_{p['id']}"):
                        client.table("profiles").update({"role": "admin"}).eq("id", p["id"]).execute()
                        st.rerun()

    st.divider()
    st.caption(
        "※ 새 사용자는 Supabase 대시보드 → Authentication → Users → Add user 에서 추가하세요. "
        "첫 로그인 시 자동으로 'user' 권한으로 등록됩니다."
    )
