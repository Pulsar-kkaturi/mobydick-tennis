"""
운영 페이지 (관리자 이상 전용)

탭 구성:
- 대회 승인: 관리자 + 마스터 모두 가능
- 유저 관리: 마스터만 가능 (유저 삭제, role 변경)
"""
import streamlit as st
import db
import auth

st.title("운영")

# 관리자(admin/master) 이상인지 확인
if not auth.is_admin():
    st.error("관리자 이상만 접근할 수 있습니다.")
    st.stop()

is_master = auth.is_master()

# 마스터만 유저 관리 탭 표시
tabs = st.tabs(["대회 승인", "유저 관리"]) if is_master else st.tabs(["대회 승인"])
tab_approval = tabs[0]
tab_users    = tabs[1] if is_master else None


# ════════════════════════════════════════════════════════════════════════════════
# 탭 1: 대회 승인 (관리자 + 마스터)
# ════════════════════════════════════════════════════════════════════════════════
with tab_approval:
    st.subheader("대회 승인 관리")
    st.caption("완료 처리된 대회를 승인하면 시즌 랭킹에 반영됩니다.")

    tournaments = db.get_tournaments()

    if not tournaments:
        st.info("대회가 없습니다.")
    else:
        finished   = [t for t in tournaments if t["is_finished"]]
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
# 탭 2: 유저 관리 (마스터만)
# ════════════════════════════════════════════════════════════════════════════════
if is_master and tab_users:
    with tab_users:
        st.subheader("유저 role 관리")
        st.caption("유저 삭제 및 role 변경은 마스터만 가능합니다.")

        client = db.get_client()
        profiles_res = client.table("profiles").select("id, role, full_name, birth_date").execute()
        profiles = profiles_res.data

        ROLE_LABELS = {
            "master": "👑 마스터",
            "admin":  "🛡️ 관리자",
            "user":   "👤 유저",
        }
        ROLE_OPTIONS = ["master", "admin", "user"]

        if not profiles:
            st.info("등록된 유저가 없습니다.")
        else:
            current_user = auth.get_user()

            for p in profiles:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    with c1:
                        me = " ← 본인" if current_user and p["id"] == current_user.id else ""
                        nm = p.get("full_name") or "(이름 없음)"
                        bd = p.get("birth_date") or "-"
                        st.markdown(f"**{nm}**{me}")
                        st.caption(f"생년월일: {bd}")
                        st.code(str(p["id"])[:20] + "...", language=None)
                    with c2:
                        st.write(ROLE_LABELS.get(p["role"], p["role"]))
                    with c3:
                        # 자기 자신의 role은 변경 불가 (실수 방지)
                        if current_user and p["id"] == current_user.id:
                            st.caption("(본인 role 변경 불가)")
                        else:
                            new_role = st.selectbox(
                                "role 변경",
                                ROLE_OPTIONS,
                                index=ROLE_OPTIONS.index(p["role"]) if p["role"] in ROLE_OPTIONS else 2,
                                key=f"role_{p['id']}",
                                label_visibility="collapsed",
                            )
                            if st.button("적용", key=f"apply_role_{p['id']}"):
                                client.table("profiles").update({"role": new_role}).eq("id", p["id"]).execute()
                                st.rerun()
                    with c4:
                        # 자기 자신은 삭제 불가
                        if not (current_user and p["id"] == current_user.id):
                            if st.button("삭제", key=f"del_user_{p['id']}"):
                                if st.session_state.get(f"confirm_del_user_{p['id']}"):
                                    client.table("profiles").delete().eq("id", p["id"]).execute()
                                    st.rerun()
                                else:
                                    st.session_state[f"confirm_del_user_{p['id']}"] = True
                                    st.warning("한 번 더 누르면 삭제됩니다.")

        st.divider()
        st.caption(
            "※ 일반 회원은 앱에서 회원가입합니다. "
            "마스터/관리자만 Supabase에서 수동 생성하거나, 가입 후 여기서 role을 올리면 됩니다."
        )
