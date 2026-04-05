"""
Supabase Auth 기반 로그인/로그아웃 + 역할(role) 관리 + 회원가입

role 계층:
  master  — 전체 권한 (유저 관리 포함)
  admin   — 마스터와 동일하나 유저 관리 불가
  user    — 대회/선수 관리 가능, 승인 불가
  None    — 게스트 (조회만)
"""
import re
import streamlit as st
import db


def validate_signup_password(password: str) -> tuple[bool, str]:
    """
    비밀번호 규칙: 8자 이상, 영문(A-Za-z) 1자 이상 + 숫자 1자 이상
    (특수문자는 선택)
    """
    if len(password) < 8:
        return False, "비밀번호는 8자 이상이어야 합니다."
    if not re.search(r"[A-Za-z]", password):
        return False, "비밀번호에 영문을 포함해 주세요."
    if not re.search(r"[0-9]", password):
        return False, "비밀번호에 숫자를 포함해 주세요."
    return True, ""


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
        res = client.auth.sign_up(
            {
                "email": em,
                "password": password,
                "options": {
                    # 트리거(up_to_date.sql)가 raw_user_meta_data 에서 읽음
                    "data": {
                        "full_name": name,
                        "birth_date": birth_str,
                    },
                },
            }
        )

        if not res.user:
            return False, "가입에 실패했습니다. 잠시 후 다시 시도해 주세요."

        uid = str(res.user.id)

        # profiles 행 생성 (일반 회원가입은 항상 role=user)
        # upsert: 이메일 확인 대기 중 트리거가 먼저 넣었을 수 있음
        try:
            client.table("profiles").upsert(
                {
                    "id": uid,
                    "role": "user",
                    "full_name": name,
                    "birth_date": birth_str,
                },
                on_conflict="id",
            ).execute()
        except Exception as pe:
            return False, (
                "가입은 되었으나 프로필 저장에 실패했습니다. "
                f"Supabase RLS 정책 또는 `migrations/up_to_date.sql` 적용을 확인해 주세요. ({pe})"
            )

        # 이메일 확인이 켜져 있으면 session이 없을 수 있음 → 로그인은 메일 확인 후
        if res.session:
            st.session_state["user"] = res.user
            st.session_state["role"] = "user"
            return True, "가입이 완료되었습니다. 로그인되었습니다."
        return True, "가입이 완료되었습니다. 이메일로 보낸 링크를 확인한 뒤 로그인해 주세요."

    except Exception as e:
        err = str(e).lower()
        if "already" in err or "registered" in err or "exists" in err:
            return False, "이미 사용 중인 이메일입니다."
        return False, f"가입 실패: {e}"


def login(email: str, password: str) -> bool:
    """이메일/비밀번호로 로그인. 성공 시 role도 함께 로드."""
    try:
        client = db.get_client()
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state["user"] = res.user
        st.session_state["role"] = _fetch_role(res.user.id)
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


def get_user():
    return st.session_state.get("user")


def get_role() -> str | None:
    return st.session_state.get("role")


def is_logged_in() -> bool:
    return "user" in st.session_state


def is_master() -> bool:
    return st.session_state.get("role") == "master"


def is_admin() -> bool:
    return st.session_state.get("role") in ("master", "admin")


def is_user() -> bool:
    return st.session_state.get("role") in ("master", "admin", "user")


def _fetch_role(user_id: str) -> str:
    """profiles 테이블에서 role 조회. 없으면 'user'로 자동 등록."""
    client = db.get_client()
    res = client.table("profiles").select("role").eq("id", user_id).execute()
    if res.data:
        return res.data[0]["role"]
    client.table("profiles").insert({"id": user_id, "role": "user"}).execute()
    return "user"
