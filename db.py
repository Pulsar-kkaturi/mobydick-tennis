"""
Supabase 클라이언트 연결 및 공통 DB 유틸리티
"""
import streamlit as st
from supabase import create_client, Client


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

def get_all_players():
    """전체 선수 풀 반환 (대회 무관)"""
    db = get_client()
    res = db.table("players").select("*").order("name").execute()
    return res.data


def upsert_global_player(name: str, player_id: int = None):
    """전체 선수 풀에 선수 추가 또는 이름 수정"""
    db = get_client()
    if player_id:
        db.table("players").update({"name": name}).eq("id", player_id).execute()
    else:
        db.table("players").insert({"name": name}).execute()


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
        .select("id, title, is_wildcard, players(id, name)")
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
            "title": row["title"],
            "is_wildcard": row["is_wildcard"],
        })
    return result


def add_player_to_tournament(tournament_id: int, player_id: int, title: str = "", is_wildcard: bool = False):
    """선수 풀에서 선수를 대회에 배정"""
    db = get_client()
    db.table("tournament_players").insert({
        "tournament_id": tournament_id,
        "player_id": player_id,
        "title": title,
        "is_wildcard": is_wildcard,
    }).execute()


def update_tournament_player(tp_id: int, title: str, is_wildcard: bool):
    """대회 내 선수의 직함/와일드카드 수정"""
    db = get_client()
    db.table("tournament_players").update({
        "title": title,
        "is_wildcard": is_wildcard,
    }).eq("id", tp_id).execute()


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
    {"item_key": "win_bonus",        "label": "경기 승리 보너스",          "is_active": True,  "score_value": 100},
    {"item_key": "play_bonus",       "label": "경기 참여 점수",            "is_active": True,  "score_value": 10},
    {"item_key": "score_diff",       "label": "게임 득실차",               "is_active": True,  "score_value": 1},
    {"item_key": "wc_self_bonus",    "label": "WC 본인 보너스",            "is_active": True,  "score_value": 30},
    {"item_key": "wc_partner_bonus", "label": "WC 파트너 보너스 (승리 시)", "is_active": True,  "score_value": 5},
    {"item_key": "extra_score",      "label": "추가 점수 (토너먼트 등)",    "is_active": True,  "score_value": 0},
]


def get_scoring_config(tournament_id: int):
    db = get_client()
    res = db.table("scoring_config").select("*").eq("tournament_id", tournament_id).execute()

    if not res.data:
        rows = [{**item, "tournament_id": tournament_id} for item in DEFAULT_SCORING_CONFIG]
        db.table("scoring_config").insert(rows).execute()
        res = db.table("scoring_config").select("*").eq("tournament_id", tournament_id).execute()

    return {row["item_key"]: row for row in res.data}


def update_scoring_config(config_id: int, is_active: bool, score_value: int):
    db = get_client()
    db.table("scoring_config").update({
        "is_active": is_active,
        "score_value": score_value,
    }).eq("id", config_id).execute()
