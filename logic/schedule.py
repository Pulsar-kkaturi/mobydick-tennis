"""
대진 자동 생성 로직

generate_schedule(): 단식/복식, 코트 수, 인당 경기 수 기반 대진 생성
- 라운드 수는 인당 경기 수와 코트/방식에 맞춰 자동 결정
- 쉬는 선수는 다음 라운드 우선 배정
- 복식: WC끼리 같은 팀 금지 (불가 시 완화)
"""
import random


def _pair_doubles(group: list, wc_map: dict):
    """
    4명을 (team1, team2) 2인 팀으로 나눔.
    WC 선수끼리 같은 팀이 되지 않는 페어링 우선 선택.
    """
    p = group[:]
    # 가능한 3가지 페어링
    pairings = [
        ([p[0], p[1]], [p[2], p[3]]),
        ([p[0], p[2]], [p[1], p[3]]),
        ([p[0], p[3]], [p[1], p[2]]),
    ]
    for t1, t2 in pairings:
        wc_clash = (wc_map.get(t1[0]) and wc_map.get(t1[1])) or \
                   (wc_map.get(t2[0]) and wc_map.get(t2[1]))
        if not wc_clash:
            return t1, t2
    # 모든 페어링에서 WC 충돌 → 첫 번째 페어링으로 강제 배정
    return pairings[0]


def generate_schedule(
    players: list,
    courts: list,
    match_type: str,
    matches_per_person: int,
    randomize: bool = True,
) -> list:
    """
    대진 자동 생성 (단식/복식 통합).

    players          : [{"name": ..., "is_wildcard": ...}, ...]
    courts           : ["A", "B"] 등 (최대 4개)
    match_type       : "복식" or "단식"
    matches_per_person: 인당 목표 경기 수
    randomize        : 선수 순서 랜덤 섞기

    반환값: matches list (round, court, team 정보, scores)
    """
    players_per_match = 4 if match_type == "복식" else 2
    active_per_round = len(courts) * players_per_match  # 한 라운드에 활동할 선수 수

    names = [p["name"] for p in players]
    wc_map = {p["name"]: p.get("is_wildcard", False) for p in players}
    n = len(names)

    if n < players_per_match:
        return []

    # 선수별 통계 초기화
    games_played = {name: 0 for name in names}
    sat_out_last = {name: False for name in names}  # 지난 라운드 쉰 선수 여부

    schedule = []
    round_num = 1
    # 안전 상한: 인당 경기 수 × 선수 수 (무한루프 방지)
    max_rounds = matches_per_person * n

    while round_num <= max_rounds:
        # 전원 목표 달성 시 종료
        if min(games_played.values()) >= matches_per_person:
            break

        # ── 이번 라운드 활성 선수 선택 ─────────────────────────────────────────
        # 정렬 기준: 경기 수 적은 순 → 지난 라운드 쉰 선수 우선 → 랜덤 타이브레이크
        sorted_names = sorted(
            names,
            key=lambda x: (
                games_played[x],           # 경기 수 적은 선수 먼저
                0 if sat_out_last[x] else 1,  # 쉬었던 선수 먼저
                random.random() if randomize else 0,
            ),
        )

        # 활성 선수 수를 players_per_match 배수로 맞춤
        active_count = min(active_per_round, n)
        active_count = (active_count // players_per_match) * players_per_match
        if active_count < players_per_match:
            break  # 최소 인원 미달

        active = sorted_names[:active_count]

        if randomize:
            random.shuffle(active)

        # ── 경기 배정 ─────────────────────────────────────────────────────────
        round_matches = []

        if match_type == "복식":
            # 4명씩 묶어 코트별로 1경기
            for ci, court in enumerate(courts):
                group = active[ci * 4:(ci + 1) * 4]
                if len(group) < 4:
                    break
                t1, t2 = _pair_doubles(group, wc_map)
                round_matches.append({
                    "round": f"R{round_num}",
                    "court": court,
                    "team1_player1": t1[0],
                    "team1_player2": t1[1],
                    "team2_player1": t2[0],
                    "team2_player2": t2[1],
                    "team1_score": None,
                    "team2_score": None,
                    "match_type": "복식",
                })
        else:  # 단식
            # 2명씩 묶어 코트별로 1경기
            for ci, court in enumerate(courts):
                group = active[ci * 2:(ci + 1) * 2]
                if len(group) < 2:
                    break
                round_matches.append({
                    "round": f"R{round_num}",
                    "court": court,
                    "team1_player1": group[0],
                    "team1_player2": None,
                    "team2_player1": group[1],
                    "team2_player2": None,
                    "team1_score": None,
                    "team2_score": None,
                    "match_type": "단식",
                })

        if not round_matches:
            break  # 더 이상 경기 배정 불가

        schedule.extend(round_matches)

        # ── 통계 업데이트 ─────────────────────────────────────────────────────
        active_this_round = set()
        for m in round_matches:
            for player in [m["team1_player1"], m.get("team1_player2"),
                           m["team2_player1"], m.get("team2_player2")]:
                if player:
                    games_played[player] += 1
                    active_this_round.add(player)

        # 이번 라운드 쉰 선수 기록
        for name in names:
            sat_out_last[name] = name not in active_this_round

        round_num += 1

    return schedule


def infer_match_type(t1: list, t2: list, wc_map: dict) -> str:
    """
    두 팀의 선수 구성을 보고 경기 유형 문자열 반환.
    wc_map: {이름: is_wildcard}
    """
    def label(name):
        return "WC" if wc_map.get(name, False) else "일반"

    t1_labels = "+".join(label(p) for p in t1 if p)
    t2_labels = "+".join(label(p) for p in t2 if p)
    return f"{t1_labels} vs {t2_labels}"
