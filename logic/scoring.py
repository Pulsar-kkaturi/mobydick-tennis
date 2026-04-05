"""
점수 계산 로직
- scoring_config 설정값을 받아 동적으로 점수를 계산
- 프리셋 적용 함수와 실제 계산 함수를 분리
"""

# ── 프리셋 정의 ───────────────────────────────────────────────────────────────
# 각 프리셋은 scoring_config의 item_key별로 (is_active, score_value) 를 덮어씀

PRESETS = {
    # 승리만 카운트 (win_score 1점)
    "승률": {
        "win_score":        (True,  1),
        "draw_score":       (False, 0),
        "loss_score":       (False, 0),
        "play_bonus":       (False, 0),
        "score_diff":       (False, 0),
        "wc_self_bonus":    (False, 0),
        "wc_partner_bonus": (False, 0),
        "extra_score":      (False, 0),
    },
    # 축구식 승점제: 승=3, 무=1, 패=0
    "승점제": {
        "win_score":        (True,  3),
        "draw_score":       (True,  1),
        "loss_score":       (False, 0),
        "play_bonus":       (False, 0),
        "score_diff":       (False, 0),
        "wc_self_bonus":    (False, 0),
        "wc_partner_bonus": (False, 0),
        "extra_score":      (False, 0),
    },
    # 게임 득실차만 반영
    "득실차": {
        "win_score":        (False, 0),
        "draw_score":       (False, 0),
        "loss_score":       (False, 0),
        "play_bonus":       (False, 0),
        "score_diff":       (True,  1),
        "wc_self_bonus":    (False, 0),
        "wc_partner_bonus": (False, 0),
        "extra_score":      (False, 0),
    },
}


def apply_preset(preset_name: str) -> dict:
    """
    프리셋 이름을 받아 scoring_config 형태의 딕셔너리로 반환.
    실제 DB 업데이트는 호출하는 쪽(페이지)에서 처리.
    """
    return PRESETS.get(preset_name, {})


def calculate_standings(players: list, matches: list, config: dict, extra_scores: list) -> list:
    """
    선수 목록, 경기 결과, 점수 설정, 추가 점수를 받아
    순위표(리스트)를 계산해 반환.

    반환값 예시:
    [
      {"name": "홍길동", "wins": 3, "played": 5, "score_diff": 4, "wc_bonus": 30,
       "partner_bonus": 0, "extra": 0, "total": 374, "rank": 1},
      ...
    ]
    """
    # 설정값 추출 (비활성화된 항목은 0으로 처리)
    def cfg(key):
        c = config.get(key, {})
        if not c.get("is_active", False):
            return 0
        return c.get("score_value", 0)

    win_pt    = cfg("win_score")
    draw_pt   = cfg("draw_score")   # 무승부 점수 (기본 off)
    loss_pt   = cfg("loss_score")   # 패배 점수 (기본 off)
    play_pt   = cfg("play_bonus")
    diff_pt   = cfg("score_diff")
    wc_self   = cfg("wc_self_bonus")
    wc_part   = cfg("wc_partner_bonus")
    extra_on  = config.get("extra_score", {}).get("is_active", True)

    # 선수 이름 → 와일드카드 여부 맵
    wc_map = {p["name"]: p["is_wildcard"] for p in players}
    # 추가 점수 맵
    extra_map = {e["player_name"]: e["score"] for e in extra_scores}

    # 선수별 통계 초기화
    stats = {p["name"]: {
        "name": p["name"],
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "played": 0,
        "score_diff": 0,
        "wc_bonus": 0,
        "partner_bonus": 0,
    } for p in players}

    for m in matches:
        s1 = m.get("team1_score")
        s2 = m.get("team2_score")
        # 점수가 입력되지 않은 경기는 건너뜀
        if s1 is None or s2 is None:
            continue

        t1 = [m["team1_player1"], m.get("team1_player2")]
        t2 = [m["team2_player1"], m.get("team2_player2")]
        t1 = [p for p in t1 if p]
        t2 = [p for p in t2 if p]

        team1_won = s1 > s2
        team2_won = s2 > s1
        is_draw   = s1 == s2  # 동점이면 무승부

        # 팀별로 통계 업데이트
        for team, won, my_score, opp_score in [
            (t1, team1_won, s1, s2),
            (t2, team2_won, s2, s1),
        ]:
            for player in team:
                if player not in stats:
                    continue
                stats[player]["played"] += 1
                stats[player]["score_diff"] += (my_score - opp_score)

                if is_draw:
                    stats[player]["draws"] += 1
                elif won:
                    stats[player]["wins"] += 1
                    # WC 파트너 보너스: 같은 팀에 WC가 있고 이겼을 때 팀원 모두에게
                    team_has_wc = any(wc_map.get(p, False) for p in team)
                    if team_has_wc:
                        stats[player]["partner_bonus"] += wc_part
                else:
                    stats[player]["losses"] += 1

            # WC 본인 보너스: WC 선수가 포함된 경기에서 경기당 1회 (승패 무관)
            for player in team:
                if wc_map.get(player, False):
                    stats[player]["wc_bonus"] += wc_self

    # 최종 점수 계산
    results = []
    for name, s in stats.items():
        extra = extra_map.get(name, 0) if extra_on else 0
        total = (
            s["wins"]         * win_pt
            + s["draws"]      * draw_pt
            + s["losses"]     * loss_pt
            + s["played"]     * play_pt
            + s["score_diff"] * diff_pt
            + s["wc_bonus"]
            + s["partner_bonus"]
            + extra
        )
        results.append({**s, "extra": extra, "total": total})

    # 총점 내림차순 → 득실차 내림차순 → 승리수 내림차순으로 정렬
    results.sort(key=lambda x: (-x["total"], -x["score_diff"], -x["wins"]))

    # 순위 부여 (동점자는 같은 순위)
    for i, r in enumerate(results):
        if i == 0:
            r["rank"] = 1
        elif r["total"] == results[i - 1]["total"]:
            r["rank"] = results[i - 1]["rank"]
        else:
            r["rank"] = i + 1

    return results


def get_season_ranking(tournaments: list, standings_map: dict) -> list:
    """
    여러 대회의 순위표를 받아 시즌 전체 랭킹 포인트를 합산.

    standings_map: {tournament_id: standings_list}
    반환: [{"name": ..., "points": ..., "detail": {...tournament_id: rank}}, ...]

    랭킹 포인트: 1위=3점, 2위=2점, 3위=1점, 4위 이하=0점
    """
    RANK_POINTS = {1: 3, 2: 2, 3: 1}

    season: dict[str, dict] = {}

    for t in tournaments:
        tid = t["id"]
        standings = standings_map.get(tid, [])
        for s in standings:
            name = s["name"]
            rank = s["rank"]
            pts = RANK_POINTS.get(rank, 0)
            if pts == 0:
                continue  # 4위 이하는 랭킹 포인트 없음
            if name not in season:
                season[name] = {"name": name, "points": 0, "detail": {}}
            season[name]["points"] += pts
            season[name]["detail"][t["name"]] = {"rank": rank, "pts": pts}

    result = sorted(season.values(), key=lambda x: -x["points"])
    return result
