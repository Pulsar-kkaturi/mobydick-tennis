"""
Supabase Auth 기반 로그인/로그아웃 + 역할(role) 관리
- session_state["user"] : 로그인한 사용자 정보
- session_state["role"] : 'admin' / 'user' / None(게스트)
"""
import streamlit as st
import db


def login(email: str, password: str) -> bool:
    """이메일/비밀번호로 로그인. 성공 시 role도 함께 로드."""
    try:
        client = db.get_client()
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state["user"] = res.user
        # profiles 테이블에서 role 조회
        st.session_state["role"] = _fetch_role(res.user.id)
        return True
    except Exception:
        return False


def logout():
    """로그아웃 후 session_state 정리."""
    try:
        db.get_client().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("user", None)
    st.session_state.pop("role", None)


def get_user():
    return st.session_state.get("user")


def get_role() -> str | None:
    """현재 사용자 role 반환. 비로그인 시 None."""
    return st.session_state.get("role")


def is_logged_in() -> bool:
    return "user" in st.session_state


def is_admin() -> bool:
    return st.session_state.get("role") == "admin"


def is_user() -> bool:
    """로그인한 일반 유저 (admin 포함)"""
    return st.session_state.get("role") in ("admin", "user")


def _fetch_role(user_id: str) -> str:
    """profiles 테이블에서 role 조회. 없으면 'user' 기본값."""
    client = db.get_client()
    res = client.table("profiles").select("role").eq("id", user_id).execute()
    if res.data:
        return res.data[0]["role"]
    # profiles 행이 없으면 기본 user로 삽입
    client.table("profiles").insert({"id": user_id, "role": "user"}).execute()
    return "user"
