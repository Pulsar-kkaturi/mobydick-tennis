"""
Supabase 클라이언트 연결 및 공통 DB 유틸리티
"""
from typing import Optional, Tuple

import streamlit as st
from supabase import create_client, Client

PAGE_SIZE = 10  # 페이지당 기본 항목 수


def get_page_slice(items: list, key: str, page_size: int = PAGE_SIZE) -> Tuple[list, bool]:
    """
    items 를 페이지네이션해서 현재 페이지 항목만 반환.
    page_size 이하면 페이지네이션 없이 전체 반환 (has_pages=False).

    사용법:
        page_items, paged = db.get_page_slice(all_items, "my_key")
        for item in page_items:
            render(item)
        if paged:
            db.render_page_nav(all_items, "my_key")
    """
    total = len(items)
    if total <= page_size:
        return items, False

    total_pages = (total + page_size - 1) // page_size
    page = max(1, min(st.session_state.get(key, 1), total_pages))
    st.session_state[key] = page

    start = (page - 1) * page_size
    return items[start : start + page_size], True


def render_page_nav(items: list, key: str, page_size: int = PAGE_SIZE) -> None:
    """get_page_slice() 로 항목을 렌더링한 뒤 호출. 이전/다음 네비게이션 표시."""
    total = len(items)
    if total <= page_size:
        return
    total_pages = (total + page_size - 1) // page_size
    page = st.session_state.get(key, 1)

    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("◀ 이전", key=f"{key}_prev", disabled=(page <= 1), use_container_width=True):
            st.session_state[key] = page - 1
            st.rerun()
    with col2:
        st.markdown(
            f"<p style='text-align:center; padding-top:6px'>{page} / {total_pages} 페이지 &nbsp;·&nbsp; 총 {total}개</p>",
            unsafe_allow_html=True,
        )
    with col3:
        if st.button("다음 ▶", key=f"{key}_next", disabled=(page >= total_pages), use_container_width=True):
            st.session_state[key] = page + 1
            st.rerun()


def render_tournament_selector() -> Optional[dict]:
    """
    대회가 필요한 페이지 상단에서 호출.
    대회 선택 selectbox를 표시하고 선택된 대회 dict를 반환한다.
    대회가 없으면 안내 메시지 후 None 반환 (호출 측에서 st.stop() 권장).
    """
    tournaments = get_tournaments()
    if not tournaments:
        st.info("등록된 대회가 없습니다. 대시보드에서 먼저 대회를 생성해 주세요.")
        return None

    t_names = [t["name"] for t in tournaments]

    # 이전에 선택한 대회 유지
    prev = st.session_state.get("selected_tournament_name")
    default_idx = t_names.index(prev) if prev in t_names else 0

    selected_name = st.selectbox("대회 선택", t_names, index=default_idx, key="page_tournament_selector")
    selected = next(t for t in tournaments if t["name"] == selected_name)

    # 사이드바 선택과 session_state 공유 (대시보드 등 다른 페이지와 연동)
    st.session_state["selected_tournament_name"] = selected_name
    st.session_state["selected_tournament"] = selected

    st.divider()
    return selected


@st.cache_resource
def get_client() -> Client:
    """Supabase 클라이언트를 싱글턴으로 반환 (앱 전체에서 재사용)"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ── 대회(Tournament) ──────────────────────────────────────────────────────────

def get_tournaments():
    db = get_client()
    res = db.table("tournaments").select("*").order("created_at", desc=True).execute()
    return res.data


def create_tournament(name: str, date: str, description: str = "", is_legacy: bool = False):
    db = get_client()
    db.table("tournaments").insert({
        "name": name,
        "date": date or None,
        "description": description,
        "is_legacy": is_legacy,
    }).execute()


def finish_tournament(tournament_id: int, finished: bool):
    db = get_client()
    db.table("tournaments").update({"is_finished": finished}).eq("id", tournament_id).execute()


def approve_tournament(tournament_id: int, approved: bool):
    """관리자가 대회를 시즌 랭킹에 반영 승인/취소"""
    db = get_client()
    db.table("tournaments").update({"is_approved": approved}).eq("id", tournament_id).execute()


def delete_tournament(tournament_id: int):
    db = get_client()
    db.table("tournaments").delete().eq("id", tournament_id).execute()


# ── 레거시 대회 순위(Legacy Results) ─────────────────────────────────────────

def get_legacy_results(tournament_id: int):
    """레거시 대회의 1~3위 결과 반환"""
    db = get_client()
    res = db.table("legacy_results").select("*").eq("tournament_id", tournament_id).order("rank").execute()
    return res.data


def set_legacy_result(tournament_id: int, rank: int, player_name: str):
    """레거시 대회 특정 순위에 선수 기록 (있으면 덮어씀)"""
    db = get_client()
    db.table("legacy_results").upsert({
        "tournament_id": tournament_id,
        "rank": rank,
        "player_name": player_name,
    }, on_conflict="tournament_id,rank").execute()


def clear_legacy_result(tournament_id: int, rank: int):
    """레거시 대회 특정 순위 기록 삭제"""
    db = get_client()
    db.table("legacy_results").delete().eq("tournament_id", tournament_id).eq("rank", rank).execute()


# ── 전체 선수 풀(Global Players) ──────────────────────────────────────────────

PLAY_STYLES = [
    "오른손 / 투핸드 백핸드",
    "왼손 / 투핸드 백핸드",
    "오른손 / 원핸드 백핸드",
    "왼손 / 원핸드 백핸드",
]

GENDERS = ["남", "여"]


def get_all_players():
    """전체 선수 풀 반환 (대회 무관)"""
    db = get_client()
    res = db.table("players").select("*").order("name").execute()
    return res.data


def upsert_global_player(name: str, player_id: int = None):
    """선수 이름 추가 또는 수정 (관리자 전용). gender/play_style은 별도 update 사용."""
    db = get_client()
    if player_id:
        db.table("players").update({"name": name}).eq("id", player_id).execute()
    else:
        # 생성 시 gender, play_style은 빈칸(None)으로 시작
        db.table("players").insert({"name": name, "gender": None, "play_style": None}).execute()


def update_player_info(player_id: int, gender: Optional[str], play_style: Optional[str]):
    """선수 추가 정보(성별, 스타일) 수정 — 유저도 가능."""
    db = get_client()
    db.table("players").update({
        "gender": gender or None,
        "play_style": play_style or None,
    }).eq("id", player_id).execute()


def delete_global_player(player_id: int):
    """전체 선수 풀에서 선수 삭제 (모든 대회 배정도 함께 삭제됨)"""
    db = get_client()
    db.table("players").delete().eq("id", player_id).execute()


# ── 대회별 선수 배정(Tournament Players) ─────────────────────────────────────

def get_tournament_players(tournament_id: int):
    """
    특정 대회에 배정된 선수 목록 반환.
    scoring/schedule 로직과 호환되도록 name, is_wildcard 필드를 포함.
    """
    db = get_client()
    res = (
        db.table("tournament_players")
        .select("id, is_wildcard, players(id, name)")
        .eq("tournament_id", tournament_id)
        .execute()
    )
    # 반환 형태를 기존 코드(scoring, schedule)와 호환되게 평탄화
    result = []
    for row in res.data:
        result.append({
            "id": row["id"],                        # tournament_players.id
            "player_id": row["players"]["id"],
            "name": row["players"]["name"],
            "is_wildcard": row["is_wildcard"],
        })
    return result


def add_player_to_tournament(tournament_id: int, player_id: int, is_wildcard: bool = False):
    """선수 풀에서 선수를 대회에 배정 (직함 필드는 사용하지 않음)"""
    db = get_client()
    db.table("tournament_players").insert({
        "tournament_id": tournament_id,
        "player_id": player_id,
        "title": None,
        "is_wildcard": is_wildcard,
    }).execute()


def update_tournament_player(tp_id: int, is_wildcard: bool):
    """대회 내 선수의 와일드카드 여부만 수정"""
    db = get_client()
    db.table("tournament_players").update({"is_wildcard": is_wildcard}).eq("id", tp_id).execute()


def remove_player_from_tournament(tp_id: int):
    """대회에서 선수 배정 해제"""
    db = get_client()
    db.table("tournament_players").delete().eq("id", tp_id).execute()


# ── 경기(Match) ───────────────────────────────────────────────────────────────

def get_matches(tournament_id: int):
    db = get_client()
    res = db.table("matches").select("*").eq("tournament_id", tournament_id).order("round").order("court").execute()
    return res.data


def upsert_match(tournament_id: int, data: dict, match_id: int = None):
    db = get_client()
    data["tournament_id"] = tournament_id
    if match_id:
        db.table("matches").update(data).eq("id", match_id).execute()
    else:
        db.table("matches").insert(data).execute()


def delete_match(match_id: int):
    db = get_client()
    db.table("matches").delete().eq("id", match_id).execute()


# ── 추가 점수(Extra Score) ────────────────────────────────────────────────────

def get_extra_scores(tournament_id: int):
    db = get_client()
    res = db.table("extra_scores").select("*").eq("tournament_id", tournament_id).execute()
    return res.data


def upsert_extra_score(tournament_id: int, player_name: str, score: int, note: str = "", score_id: int = None):
    db = get_client()
    data = {"tournament_id": tournament_id, "player_name": player_name, "score": score, "note": note}
    if score_id:
        db.table("extra_scores").update(data).eq("id", score_id).execute()
    else:
        db.table("extra_scores").insert(data).execute()


def delete_extra_score(score_id: int):
    db = get_client()
    db.table("extra_scores").delete().eq("id", score_id).execute()


# ── 점수 설정(Scoring Config) ─────────────────────────────────────────────────

DEFAULT_SCORING_CONFIG = [
    {"item_key": "win_score",        "label": "승리",                      "is_active": True,  "score_value": 1},
    {"item_key": "draw_score",       "label": "무승부",                    "is_active": False, "score_value": 0},
    {"item_key": "loss_score",       "label": "패배",                      "is_active": False, "score_value": 0},
    {"item_key": "play_bonus",       "label": "경기 참여",                  "is_active": False, "score_value": 0},
    {"item_key": "score_diff",       "label": "게임 득실차",                "is_active": False, "score_value": 1},
    {"item_key": "wc_self_bonus",    "label": "WC 본인 보너스",             "is_active": False, "score_value": 0},
    {"item_key": "wc_partner_bonus", "label": "WC 파트너 보너스 (승리 시)", "is_active": False, "score_value": 0},
    {"item_key": "extra_score",      "label": "추가 점수",                  "is_active": False, "score_value": 0},
]


def get_scoring_config(tournament_id: int):
    """
    대회별 점수 설정 로드.
    항목이 없으면 기본값으로 생성, 일부만 없으면 해당 항목만 추가 (신규 item_key 대응).
    """
    db = get_client()
    res = db.table("scoring_config").select("*").eq("tournament_id", tournament_id).execute()
    existing_keys = {row["item_key"] for row in res.data}

    if not existing_keys:
        rows = [{**item, "tournament_id": tournament_id} for item in DEFAULT_SCORING_CONFIG]
        db.table("scoring_config").insert(rows).execute()
    else:
        # 새로 추가된 항목(draw_score, loss_score 등)이 기존 대회에 없으면 삽입
        missing = [item for item in DEFAULT_SCORING_CONFIG if item["item_key"] not in existing_keys]
        if missing:
            rows = [{**item, "tournament_id": tournament_id} for item in missing]
            db.table("scoring_config").insert(rows).execute()

    res = db.table("scoring_config").select("*").eq("tournament_id", tournament_id).execute()
    return {row["item_key"]: row for row in res.data}


def update_scoring_config(config_id: int, is_active: bool, score_value: int):
    db = get_client()
    db.table("scoring_config").update({
        "is_active": is_active,
        "score_value": score_value,
    }).eq("id", config_id).execute()
