"""
Supabase Auth 기반 로그인/로그아웃 + 역할(role) 관리 + 회원가입

role 계층:
  master  — 전체 권한 (유저 관리 포함)
  admin   — 마스터와 동일하나 유저 관리 불가
  user    — 대회/선수 관리 가능, 승인 불가
  None    — 게스트 (조회만)
"""
import re
from typing import Optional

import streamlit as st
import db


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def validate_signup_password(password: str) -> tuple[bool, str]:
    """비밀번호 규칙: 8자 이상, 영문+숫자 각 1자 이상."""
    if len(password) < 8:
        return False, "비밀번호는 8자 이상이어야 합니다."
    if not re.search(r"[A-Za-z]", password):
        return False, "비밀번호에 영문을 포함해 주세요."
    if not re.search(r"[0-9]", password):
        return False, "비밀번호에 숫자를 포함해 주세요."
    return True, ""


def _fetch_role(user_id: str) -> str:
    """profiles 테이블에서 role 조회. 없으면 'user'로 자동 등록."""
    client = db.get_client()
    res = client.table("profiles").select("role").eq("id", user_id).execute()
    if res.data:
        return res.data[0]["role"]
    client.table("profiles").insert({"id": user_id, "role": "user"}).execute()
    return "user"


def _set_session_state(user) -> None:
    """로그인 성공 후 공통 session_state 세팅."""
    st.session_state["user"] = user
    st.session_state["role"] = _fetch_role(str(user.id))


# ── 회원가입 ─────────────────────────────────────────────────────────────────

def signup(full_name: str, email: str, password: str, birth_date) -> tuple[bool, str]:
    """
    앱에서 일반 유저 회원가입.
    성공 시 (True, 안내 메시지), 실패 시 (False, 에러 메시지).
    birth_date: datetime.date 또는 None
    """
    name = (full_name or "").strip()
    em = (email or "").strip()
    if not name:
        return False, "이름을 입력해 주세요."
    if not em:
        return False, "이메일을 입력해 주세요."
    ok, msg = validate_signup_password(password)
    if not ok:
        return False, msg
    if birth_date is None:
        return False, "생년월일을 선택해 주세요."

    birth_str = birth_date.isoformat() if hasattr(birth_date, "isoformat") else str(birth_date)

    try:
        client = db.get_client()
        res = client.auth.sign_up({
            "email": em,
            "password": password,
            "options": {
                # 트리거(up_to_date.sql)가 raw_user_meta_data 에서 읽음
                "data": {"full_name": name, "birth_date": birth_str},
            },
        })

        if not res.user:
            return False, "가입에 실패했습니다. 잠시 후 다시 시도해 주세요."

        uid = str(res.user.id)
        try:
            client.table("profiles").upsert(
                {"id": uid, "role": "user", "full_name": name, "birth_date": birth_str, "email": em},
                on_conflict="id",
            ).execute()
        except Exception as pe:
            return False, (
                "가입은 되었으나 프로필 저장에 실패했습니다. "
                f"RLS 정책 또는 migrations/up_to_date.sql 적용을 확인해 주세요. ({pe})"
            )

        # Confirm email OFF 상태면 세션이 바로 옴 → 즉시 로그인
        if res.session:
            _set_session_state(res.user)
            return True, "가입이 완료되었습니다. 로그인되었습니다."
        return True, "가입이 완료되었습니다. 이메일 링크를 확인한 뒤 로그인해 주세요."

    except Exception as e:
        err = str(e).lower()
        if "already" in err or "registered" in err or "exists" in err:
            return False, "이미 사용 중인 이메일입니다."
        return False, f"가입 실패: {e}"


# ── 로그인 / 로그아웃 ─────────────────────────────────────────────────────────

def login(email: str, password: str) -> bool:
    """이메일/비밀번호 로그인. 성공 시 role 도 로드."""
    try:
        client = db.get_client()
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        _set_session_state(res.user)
        # profiles.email 동기화 (구 계정용)
        try:
            em = (res.user.email or "").strip()
            if em:
                client.table("profiles").update({"email": em}).eq("id", str(res.user.id)).execute()
        except Exception:
            pass
        return True
    except Exception:
        return False


def logout():
    try:
        db.get_client().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("user", None)
    st.session_state.pop("role", None)
    st.session_state.pop("otp_reset_email", None)   # OTP 재설정 진행 중이었으면 함께 제거


# ── OTP 비밀번호 재설정 ──────────────────────────────────────────────────────

def send_reset_otp(email: str) -> tuple[bool, str]:
    """
    비밀번호 재설정용 6자리 OTP 를 이메일로 발송.
    Supabase 이메일 템플릿에서 {{ .Token }} 이 들어가야 숫자 코드가 노출됨.
    (기본 템플릿은 링크지만, Supabase 대시보드 Emails → Magic Link 에서 {{ .Token }} 으로 교체 가능)
    """
    em = (email or "").strip()
    if not em:
        return False, "이메일을 입력해 주세요."
    try:
        client = db.get_client()
        # should_create_user=False → 가입된 이메일에만 OTP 발송
        client.auth.sign_in_with_otp({
            "email": em,
            "options": {"should_create_user": False},
        })
        return True, "6자리 코드를 이메일로 보냈습니다. 메일함(스팸 포함)을 확인해 주세요."
    except Exception as e:
        err = str(e).lower()
        if "user not found" in err or "not found" in err or "no user" in err:
            return False, "가입된 이메일이 아닙니다."
        return False, f"발송 실패: {e}"


def verify_reset_otp(email: str, token: str) -> tuple[bool, str]:
    """
    6자리 OTP 검증. 성공 시 로그인 세션이 만들어짐.
    이후 session_state['otp_reset_mode'] = True 로 비밀번호 변경 폼을 표시.
    """
    em = (email or "").strip()
    tok = (token or "").strip()
    if not tok:
        return False, "코드를 입력해 주세요."
    try:
        client = db.get_client()
        # type="email" → magiclink/OTP 로그인 플로우
        res = client.auth.verify_otp({"email": em, "token": tok, "type": "email"})
        if not res.user:
            return False, "인증에 실패했습니다. 코드를 다시 확인해 주세요."
        _set_session_state(res.user)
        st.session_state["otp_reset_mode"] = True
        return True, "인증 완료. 새 비밀번호를 설정해 주세요."
    except Exception as e:
        err = str(e).lower()
        if "invalid" in err or "expired" in err or "otp" in err:
            return False, "코드가 올바르지 않거나 만료되었습니다."
        return False, f"인증 실패: {e}"


def is_otp_reset_mode() -> bool:
    return bool(st.session_state.get("otp_reset_mode"))


def submit_new_password(password: str, password_confirm: str) -> tuple[bool, str]:
    """OTP 인증 후 새 비밀번호 저장."""
    if password != password_confirm:
        return False, "비밀번호 확인이 일치하지 않습니다."
    ok, msg = validate_signup_password(password)
    if not ok:
        return False, msg
    try:
        client = db.get_client()
        client.auth.update_user({"password": password})
        st.session_state.pop("otp_reset_mode", None)
        # profiles.email 동기화
        try:
            u = st.session_state.get("user")
            if u and getattr(u, "email", None):
                client.table("profiles").update({"email": u.email}).eq("id", str(u.id)).execute()
        except Exception:
            pass
        return True, "비밀번호가 변경되었습니다."
    except Exception as e:
        return False, f"변경 실패: {e}"


# ── session_state 접근자 ─────────────────────────────────────────────────────

def get_user():
    return st.session_state.get("user")


def get_role() -> Optional[str]:
    return st.session_state.get("role")


def is_logged_in() -> bool:
    return "user" in st.session_state


def is_master() -> bool:
    return st.session_state.get("role") == "master"


def is_admin() -> bool:
    return st.session_state.get("role") in ("master", "admin")


def is_user() -> bool:
    return st.session_state.get("role") in ("master", "admin", "user")
