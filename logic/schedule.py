"""
대진 자동 생성 로직 - 라운드 로빈 방식
복식 기준: 선수를 2인 1조로 묶어 라운드별 대진 생성
"""
import random
from itertools import combinations


def generate_doubles_schedule(players: list, courts: list = None, randomize: bool = True) -> list:
    """
    선수 목록을 받아 복식 라운드 로빈 대진표 생성.

    - 4명씩 2팀(2+2)으로 묶어 한 경기를 만듦
    - 가능한 모든 선수 조합을 커버하도록 라운드를 구성
    - 코트 수 기본값: A, B

    반환값: [{"round": "R1", "court": "A", "team1": [...], "team2": [...]}, ...]
    """
    if courts is None:
        courts = ["A", "B"]

    if randomize:
        players = players[:]
        random.shuffle(players)

    # 선수 이름만 추출
    names = [p["name"] for p in players]
    n = len(names)

    if n < 4:
        return []

    # 모든 2인 팀 조합
    all_teams = list(combinations(names, 2))
    # 모든 경기 조합: 두 팀이 겹치지 않는 쌍
    all_matches = [
        (t1, t2)
        for i, t1 in enumerate(all_teams)
        for t2 in all_teams[i + 1:]
        if not set(t1) & set(t2)  # 선수 중복 없어야 함
    ]

    if randomize:
        random.shuffle(all_matches)

    # 라운드별로 경기 배정
    # 같은 라운드 안에서 선수가 2번 나오면 안 됨 + 코트 수 제한
    schedule = []
    remaining = all_matches[:]
    round_num = 1

    while remaining:
        used_players = set()
        round_matches = []

        for match in remaining[:]:
            t1, t2 = match
            involved = set(t1) | set(t2)
            if not involved & used_players and len(round_matches) < len(courts):
                round_matches.append(match)
                used_players |= involved
                remaining.remove(match)

        for i, (t1, t2) in enumerate(round_matches):
            schedule.append({
                "round": f"R{round_num}",
                "court": courts[i % len(courts)],
                "team1_player1": t1[0],
                "team1_player2": t1[1],
                "team2_player1": t2[0],
                "team2_player2": t2[1],
                "team1_score": None,
                "team2_score": None,
                "match_type": "",
            })
        round_num += 1

    return schedule


def infer_match_type(t1: list, t2: list, wc_map: dict) -> str:
    """
    두 팀의 선수 구성을 보고 경기 유형 문자열 반환.
    wc_map: {이름: is_wildcard}
    """
    def label(name):
        return "WC" if wc_map.get(name, False) else "일반"

    t1_labels = "+".join(label(p) for p in t1)
    t2_labels = "+".join(label(p) for p in t2)
    return f"{t1_labels} vs {t2_labels}"
