"""
대진 자동 생성 로직

generate_schedule(): 단식/복식, 코트 수, 인당 경기 수 기반 대진 생성
- 라운드 수는 인당 경기 수와 코트/방식에 맞춰 자동 결정
- 쉬는 선수는 다음 라운드 우선 배정
- 복식: WC끼리 같은 팀 금지 (불가 시 완화)
- 단식: 같은 상대 재대결 최소화
- 복식: 같은 팀 조합 / 같은 매치업 재등장 최소화
"""
import random
from itertools import combinations


def recommend_matches_per_person(player_count: int, match_type: str) -> int:
    """
    경기 방식별 추천 인당 경기 수(표시용).
    - 단식: 서로 한 번씩 만나는 기준 n-1
    - 복식: 팀/매치업 중복을 최대한 피하는 보수적 기준으로 n-1
    """
    if player_count <= 0:
        return 0
    if match_type == "복식" and player_count < 4:
        return 0
    if match_type == "단식" and player_count < 2:
        return 0
    return max(1, player_count - 1)


def _team_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def _matchup_key(team1: tuple[str, str], team2: tuple[str, str]) -> tuple[tuple[str, str], tuple[str, str]]:
    return tuple(sorted((team1, team2)))


def _pairings_for_group(group: list[str]) -> list[tuple[list[str], list[str]]]:
    """4명을 2:2로 나누는 가능한 3개 페어링."""
    p = group[:]
    return [
        ([p[0], p[1]], [p[2], p[3]]),
        ([p[0], p[2]], [p[1], p[3]]),
        ([p[0], p[3]], [p[1], p[2]]),
    ]


def _pick_best_doubles_match(
    available: list[str],
    wc_map: dict[str, bool],
    team_pair_count: dict[tuple[str, str], int],
    matchup_count: dict[tuple[tuple[str, str], tuple[str, str]], int],
    randomize: bool,
):
    """
    남은 선수들 중 1경기를 선택:
    1) 팀 조합 재사용 최소화
    2) 같은 매치업 재사용 최소화
    3) WC끼리 같은 팀 방지 우선
    """
    if len(available) < 4:
        return None

    best = None
    best_score = None

    for group_tuple in combinations(available, 4):
        group = list(group_tuple)
        for t1, t2 in _pairings_for_group(group):
            t1_key = _team_key(t1[0], t1[1])
            t2_key = _team_key(t2[0], t2[1])
            mu_key = _matchup_key(t1_key, t2_key)

            wc_clash = (wc_map.get(t1[0], False) and wc_map.get(t1[1], False)) or (
                wc_map.get(t2[0], False) and wc_map.get(t2[1], False)
            )
            score = (
                team_pair_count.get(t1_key, 0) + team_pair_count.get(t2_key, 0),
                matchup_count.get(mu_key, 0),
                1 if wc_clash else 0,
                random.random() if randomize else 0.0,
            )

            if best_score is None or score < best_score:
                best_score = score
                best = (group, t1, t2, t1_key, t2_key, mu_key)

    return best


def _build_singles_cycle_exact(names: list[str], courts: list[str], randomize: bool) -> list[list[tuple[str, str, str]]]:
    """
    단식 1회전(모든 페어 1회씩) 경기 블록 생성.
    반환: [[(court, p1, p2), ...], ...] 형태 (라운드 블록 리스트)
    """
    all_pairs = list(combinations(names, 2))
    if randomize:
        random.shuffle(all_pairs)

    remaining = all_pairs[:]
    blocks: list[list[tuple[str, str, str]]] = []

    while remaining:
        used: set[str] = set()
        picked_idx: list[int] = []
        block_pairs: list[tuple[str, str]] = []

        for idx, (a, b) in enumerate(remaining):
            if len(block_pairs) >= len(courts):
                break
            if a in used or b in used:
                continue
            block_pairs.append((a, b))
            picked_idx.append(idx)
            used.add(a)
            used.add(b)

        if not block_pairs:
            a, b = remaining[0]
            block_pairs.append((a, b))
            picked_idx = [0]

        for idx in reversed(picked_idx):
            remaining.pop(idx)

        block_matches: list[tuple[str, str, str]] = []
        for ci, (a, b) in enumerate(block_pairs):
            block_matches.append((courts[ci], a, b))
        blocks.append(block_matches)

    return blocks


def _pair_doubles(group: list, wc_map: dict):
    """
    4명을 (team1, team2) 2인 팀으로 나눔.
    WC 선수끼리 같은 팀이 되지 않는 페어링 우선 선택.
    """
    p = group[:]
    # 가능한 3가지 페어링
    pairings = _pairings_for_group(p)
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
    repeat_count: int,
    randomize: bool = True,
) -> list:
    """
    대진 자동 생성 (단식/복식 통합).

    players          : [{"name": ..., "is_wildcard": ...}, ...]
    courts           : ["A", "B"] 등 (최대 4개)
    match_type       : "복식" or "단식"
    repeat_count     : 반복 수 (1회전, 2회전, ...)
    randomize        : 선수 순서 랜덤 섞기

    반환값: matches list (round, court, team 정보, scores)
    """
    names = [p["name"] for p in players]
    wc_map = {p["name"]: p.get("is_wildcard", False) for p in players}
    n = len(names)

    if repeat_count < 1:
        return []

    players_per_match = 4 if match_type == "복식" else 2
    active_per_round = len(courts) * players_per_match  # 한 라운드에 활동할 선수 수

    if n < players_per_match or not courts:
        return []

    # ── 단식: 정확반복(각 페어 1회전 구성 후 repeat_count만큼 반복) ───────────
    if match_type == "단식":
        cycle_blocks = _build_singles_cycle_exact(names, courts, randomize)
        schedule = []
        round_num = 1
        for _ in range(int(repeat_count)):
            blocks = cycle_blocks[:]
            if randomize:
                random.shuffle(blocks)
            for block in blocks:
                for court, p1, p2 in block:
                    schedule.append({
                        "round": f"R{round_num}",
                        "court": court,
                        "team1_player1": p1,
                        "team1_player2": None,
                        "team2_player1": p2,
                        "team2_player2": None,
                        "team1_score": None,
                        "team2_score": None,
                        "match_type": "단식",
                    })
                round_num += 1
        return schedule

    # 선수별 통계 초기화
    games_played = {name: 0 for name in names}
    sat_out_last = {name: False for name in names}  # 지난 라운드 쉰 선수 여부
    singles_pair_count: dict[frozenset, int] = {}
    doubles_team_count: dict[tuple[str, str], int] = {}
    doubles_matchup_count: dict[tuple[tuple[str, str], tuple[str, str]], int] = {}

    schedule = []
    round_num = 1
    # 안전 상한: 인당 경기 수 × 선수 수 (무한루프 방지)
    base_matches_per_person = recommend_matches_per_person(n, match_type)
    max_rounds = base_matches_per_person * n

    while round_num <= max_rounds:
        # 전원 목표 달성 시 종료
        if min(games_played.values()) >= base_matches_per_person:
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
            available = active[:]
            if randomize:
                random.shuffle(available)
            for court in courts:
                if len(available) < 4:
                    break
                picked = _pick_best_doubles_match(
                    available,
                    wc_map,
                    doubles_team_count,
                    doubles_matchup_count,
                    randomize,
                )
                if not picked:
                    break
                group, t1, t2, t1_key, t2_key, mu_key = picked
                for name in group:
                    if name in available:
                        available.remove(name)
                doubles_team_count[t1_key] = doubles_team_count.get(t1_key, 0) + 1
                doubles_team_count[t2_key] = doubles_team_count.get(t2_key, 0) + 1
                doubles_matchup_count[mu_key] = doubles_matchup_count.get(mu_key, 0) + 1
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
            available = active[:]
            if randomize:
                random.shuffle(available)
            for court in courts:
                if len(available) < 2:
                    break
                p1 = available.pop(0)
                candidates = []
                for idx, p2 in enumerate(available):
                    pair_key = frozenset((p1, p2))
                    candidates.append((singles_pair_count.get(pair_key, 0), random.random() if randomize else 0.0, idx, p2))
                if not candidates:
                    break
                _, _, remove_idx, p2 = min(candidates)
                available.pop(remove_idx)
                pair_key = frozenset((p1, p2))
                singles_pair_count[pair_key] = singles_pair_count.get(pair_key, 0) + 1
                round_matches.append({
                    "round": f"R{round_num}",
                    "court": court,
                    "team1_player1": p1,
                    "team1_player2": None,
                    "team2_player1": p2,
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

    # 복식은 1회전 생성 결과를 repeat_count만큼 정확 반복
    if not schedule:
        return []

    cycle_schedule = schedule[:]
    cycle_rounds: dict[str, list[dict]] = {}
    for m in cycle_schedule:
        cycle_rounds.setdefault(m["round"], []).append(m)
    ordered_round_keys = sorted(cycle_rounds.keys(), key=lambda x: int(str(x).lstrip("R")) if str(x).lstrip("R").isdigit() else 10**9)

    final_schedule = []
    round_num = 1
    for _ in range(int(repeat_count)):
        for rk in ordered_round_keys:
            round_matches = cycle_rounds[rk][:]
            if randomize:
                random.shuffle(round_matches)
            for m in round_matches:
                copied = {**m}
                copied["round"] = f"R{round_num}"
                final_schedule.append(copied)
            round_num += 1
    return final_schedule


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
