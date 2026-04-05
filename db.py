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
    """전체 대회 목록 반환 (최신순)"""
    db = get_client()
    res = db.table("tournaments").select("*").order("created_at", desc=True).execute()
    return res.data


def create_tournament(name: str, date: str, description: str = ""):
    db = get_client()
    db.table("tournaments").insert({
        "name": name,
        "date": date or None,
        "description": description,
    }).execute()


def finish_tournament(tournament_id: int, finished: bool):
    db = get_client()
    db.table("tournaments").update({"is_finished": finished}).eq("id", tournament_id).execute()


def delete_tournament(tournament_id: int):
    db = get_client()
    db.table("tournaments").delete().eq("id", tournament_id).execute()


# ── 선수(Player) ──────────────────────────────────────────────────────────────

def get_players(tournament_id: int):
    """대회별 선수 목록"""
    db = get_client()
    res = db.table("players").select("*").eq("tournament_id", tournament_id).order("id").execute()
    return res.data


def upsert_player(tournament_id: int, name: str, title: str, is_wildcard: bool, player_id: int = None):
    db = get_client()
    data = {"tournament_id": tournament_id, "name": name, "title": title, "is_wildcard": is_wildcard}
    if player_id:
        db.table("players").update(data).eq("id", player_id).execute()
    else:
        db.table("players").insert(data).execute()


def delete_player(player_id: int):
    db = get_client()
    db.table("players").delete().eq("id", player_id).execute()


# ── 경기(Match) ───────────────────────────────────────────────────────────────

def get_matches(tournament_id: int):
    """대회별 경기 목록"""
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

# 기본 점수 설정값 (대회 처음 생성 시 이 값으로 초기화)
DEFAULT_SCORING_CONFIG = [
    {"item_key": "win_bonus",       "label": "경기 승리 보너스",        "is_active": True,  "score_value": 100},
    {"item_key": "play_bonus",      "label": "경기 참여 점수",          "is_active": True,  "score_value": 10},
    {"item_key": "score_diff",      "label": "게임 득실차",             "is_active": True,  "score_value": 1},
    {"item_key": "wc_self_bonus",   "label": "WC 본인 보너스",          "is_active": True,  "score_value": 30},
    {"item_key": "wc_partner_bonus","label": "WC 파트너 보너스 (승리 시)", "is_active": True, "score_value": 5},
    {"item_key": "extra_score",     "label": "추가 점수 (토너먼트 등)",  "is_active": True,  "score_value": 0},
]


def get_scoring_config(tournament_id: int):
    """대회별 점수 설정 조회. 없으면 기본값으로 초기화 후 반환."""
    db = get_client()
    res = db.table("scoring_config").select("*").eq("tournament_id", tournament_id).execute()

    if not res.data:
        # 대회에 설정이 없으면 기본값 삽입
        rows = [{**item, "tournament_id": tournament_id} for item in DEFAULT_SCORING_CONFIG]
        db.table("scoring_config").insert(rows).execute()
        res = db.table("scoring_config").select("*").eq("tournament_id", tournament_id).execute()

    # item_key를 키로 하는 딕셔너리로 변환해서 반환
    return {row["item_key"]: row for row in res.data}


def update_scoring_config(config_id: int, is_active: bool, score_value: int):
    db = get_client()
    db.table("scoring_config").update({
        "is_active": is_active,
        "score_value": score_value,
    }).eq("id", config_id).execute()
