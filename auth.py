"""
Supabase Auth 기반 로그인/로그아웃 + 역할(role) 관리 + 회원가입

role 계층:
  master  — 전체 권한 (유저 관리 포함)
  admin   — 마스터와 동일하나 유저 관리 불가
  user    — 대회/선수 관리 가능, 승인 불가
  None    — 게스트 (조회만)
"""
import base64
import json
import re
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components
import db


def _jwt_amr_includes_recovery(access_token: str) -> bool:
    """
    재설정용 access_token JWT payload 의 amr 에 'recovery' 가 들어가는 경우가 많다.
    (서명 검증 없이 디코드만 — 링크 조작 방지는 set_session 시 Supabase 가 판별)
    """
    try:
        parts = access_token.split(".")
        if len(parts) < 2:
            return False
        b64 = parts[1]
        pad = "=" * (-len(b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(b64 + pad).decode("utf-8"))
        amr = payload.get("amr")
        return isinstance(amr, list) and "recovery" in amr
    except Exception:
        return False


def _qp_first(qp, key: str) -> Optional[str]:
    """st.query_params 값이 문자열 또는 리스트일 때 첫 문자열만 꺼냄."""
    v = qp.get(key)
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return str(v[0]) if v else None
    return str(v)


def inject_recovery_hash_to_query_redirect():
    """
    비밀번호 재설정 메일 링크는 브라우저 주소가
      https://앱/#access_token=...&refresh_token=...&type=recovery
    처럼 오는 경우가 많다. # 뒤(해시)는 HTTP 요청에 안 실리므로 Streamlit(파이썬)이 못 읽는다.

    주의: st.components.html 은 iframe 안에서 실행된다. iframe 의 window.location 에는
    해시가 없으므로, 반드시 window.top (또는 parent) 의 location 을 봐야 한다.
    """
    components.html(
        """
<script>
(function () {
  function pageLocation() {
    try {
      if (window.top && window.top.location) return window.top.location;
    } catch (e) {}
    try {
      if (window.parent && window.parent.location) return window.parent.location;
    } catch (e) {}
    return window.location;
  }
  var loc = pageLocation();
  var h = loc.hash;
  if (!h || h.length < 2) return;
  var s = h.substring(1);
  // 재설정 플로우만 옮김 (일반 OAuth implicit 과 섞이면 안 됨)
  if (s.indexOf("access_token") === -1) return;
  if (s.indexOf("type=recovery") === -1 && s.indexOf("type%3Drecovery") === -1) return;
  var path = loc.pathname;
  var search = loc.search || "";
  var join = search ? "&" : "?";
  loc.replace(loc.origin + path + search + join + s);
})();
</script>
        """,
        height=1,
        width=1,
    )


def _sync_session_state_from_supabase_client(client) -> None:
    """Supabase 클라이언트에 잡힌 세션을 앱이 쓰는 session_state 와 맞춤."""
    gu = client.auth.get_user()
    if gu and getattr(gu, "user", None):
        uid = str(gu.user.id)
        st.session_state["user"] = gu.user
        st.session_state["role"] = _fetch_role(uid)


def _strip_oauth_query_params() -> None:
    """주소창에서 토큰·code 가 남지 않게 제거(히스토리/공유 시 노출 방지)."""
    qp = st.query_params
    drop = frozenset(
        ("access_token", "refresh_token", "type", "expires_in", "token_type", "code", "scope", "state")
    )
    for k in list(qp.keys()):
        if k in drop:
            del qp[k]


def try_consume_password_recovery_redirect() -> None:
    """
    URL 쿼리에 recovery 토큰 또는 PKCE code 가 있으면 세션으로 바꾼 뒤
    password_recovery_mode 를 켠다. 이후 app.py 에서 새 비밀번호 폼을 보여 준다.
    """
    qp = st.query_params
    at = _qp_first(qp, "access_token")
    rt = _qp_first(qp, "refresh_token")
    tp = (_qp_first(qp, "type") or "").lower()

    client = db.get_client()

    # 해시→쿼리로 넘어온 implicit 형태 (type=recovery 또는 JWT amr 에 recovery)
    # 참고: ?code= 만 오는 PKCE 는 code_verifier 가 브라우저에 있어야 해서
    # Streamlit 파이썬만으로는 교환 불가. 이 경우 Supabase 쪽이 해시 토큰으로 오게 하는 설정을 쓰는 편이 낫다.
    is_recovery = tp == "recovery" or _jwt_amr_includes_recovery(at or "")
    if at and rt and is_recovery:
        try:
            resp = client.auth.set_session(access_token=at, refresh_token=rt)
            # get_user() 가 비는 경우가 있어 set_session 응답을 우선 사용
            u = getattr(resp, "user", None) if resp is not None else None
            if u is not None:
                st.session_state["user"] = u
                st.session_state["role"] = _fetch_role(str(u.id))
            else:
                _sync_session_state_from_supabase_client(client)
            st.session_state["password_recovery_mode"] = True
            _strip_oauth_query_params()
            st.rerun()
        except Exception as e:
            st.error(f"재설정 링크 처리에 실패했습니다. 링크가 만료됐을 수 있습니다. ({e})")


def is_password_recovery_mode() -> bool:
    return bool(st.session_state.get("password_recovery_mode"))


def submit_new_password_after_recovery(password: str, password_confirm: str) -> tuple[bool, str]:
    """
    recovery 세션으로 로그인된 상태에서만 호출.
    Supabase 규칙: update_user({"password"}) 전에 세션이 있어야 함.
    """
    if password != password_confirm:
        return False, "비밀번호 확인이 일치하지 않습니다."
    ok, msg = validate_signup_password(password)
    if not ok:
        return False, msg
    if not st.session_state.get("password_recovery_mode"):
        return False, "재설정 세션이 없습니다. 메일의 링크를 다시 열어 주세요."

    try:
        client = db.get_client()
        client.auth.update_user({"password": password})
        st.session_state.pop("password_recovery_mode", None)
        _sync_session_state_from_supabase_client(client)
        # profiles.email 동기화 (로그인 플로우와 동일)
        try:
            u = st.session_state.get("user")
            if u and getattr(u, "email", None):
                uid = str(u.id)
                em = (u.email or "").strip()
                if em:
                    client.table("profiles").update({"email": em}).eq("id", uid).execute()
        except Exception:
            pass
        return True, "비밀번호가 변경되었습니다. 이제 그대로 이용하시면 됩니다."
    except Exception as e:
        return False, f"변경 실패: {e}"


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
                    "email": em,
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


def send_password_reset_email(email: str) -> tuple[bool, str]:
    """
    비밀번호 재설정 메일 발송 (Supabase 기본 플로우).
    사용자는 메일의 링크를 눌러 새 비밀번호를 설정합니다.
    Streamlit Cloud 사용 시 Supabase Auth에 Site URL / Redirect URLs 등록 필요.
    """
    em = (email or "").strip()
    if not em:
        return False, "이메일을 입력해 주세요."
    try:
        client = db.get_client()
        opts: dict = {}
        # secrets.toml 에 있으면 재설정 완료 후 이 주소로 리다이렉트
        if "PASSWORD_RESET_REDIRECT_URL" in st.secrets:
            opts["redirect_to"] = st.secrets["PASSWORD_RESET_REDIRECT_URL"]
        client.auth.reset_password_for_email(em, options=opts or None)
        return True, "재설정 안내 메일을 보냈습니다. 메일함(스팸함 포함)을 확인해 주세요."
    except Exception as e:
        return False, f"요청 실패: {e}"


def login(email: str, password: str) -> bool:
    """이메일/비밀번호로 로그인. 성공 시 role도 함께 로드."""
    try:
        client = db.get_client()
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state["user"] = res.user
        st.session_state["role"] = _fetch_role(res.user.id)
        # profiles.email 이 비어 있을 때(구 계정) 운영 화면 표시용으로 동기화
        try:
            uid = str(res.user.id)
            em = (res.user.email or "").strip()
            if em:
                client.table("profiles").update({"email": em}).eq("id", uid).execute()
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
    st.session_state.pop("password_recovery_mode", None)


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


def _fetch_role(user_id: str) -> str:
    """profiles 테이블에서 role 조회. 없으면 'user'로 자동 등록."""
    client = db.get_client()
    res = client.table("profiles").select("role").eq("id", user_id).execute()
    if res.data:
        return res.data[0]["role"]
    client.table("profiles").insert({"id": user_id, "role": "user"}).execute()
    return "user"
