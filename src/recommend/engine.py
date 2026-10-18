"""Recommendation engine: generate N sets of 6 numbers."""

import random
import time
from typing import List, Dict, Optional, Callable

from .. import config
from ..analysis import stats as S
from ..data.models import Draw
from . import filters as F
from . import scorer as SC


STRATEGIES = ["balanced", "hot", "cold", "frequency", "recent", "pattern"]


def _weights(strategy, draws, number_scores):
    w = [0.0] * (config.LOTTO_MAX + 1)
    overall = S.frequency(draws) if draws else [0] * 46
    recent = S.recent_frequency(draws, config.RECENT_WINDOW) if draws else [0] * 46
    cold_list = S.cold_numbers(draws, config.HOT_COLD_WINDOW, 45) if draws else list(range(1, 46))
    cold_set = set(cold_list[:15])

    if strategy == "hot":
        # 최근 핫 번호에 강하게 집중 (hot 목록에 가중, 나머지는 낮게)
        hot_set = set(S.hot_numbers(draws, config.HOT_COLD_WINDOW, 12)) if draws else set()
        for n in range(1, 46):
            w[n] = (recent[n] + 1) * (2.0 if n in hot_set else 0.5)
    elif strategy == "cold":
        for n in range(1, 46):
            w[n] = 1.0 / (recent[n] + 1) + (0.5 if n in cold_set else 0)
    elif strategy == "frequency":
        for n in range(1, 46):
            w[n] = overall[n] + 1
    elif strategy == "recent":
        for n in range(1, 46):
            w[n] = recent[n] + 1
    elif strategy == "pattern":
        # 번호 편향 없이 균등 샘플링 → 제약/패턴 점수로만 선별
        for n in range(1, 46):
            w[n] = 1.0
        return w
    else:  # balanced
        for n in range(1, 46):
            # blend overall + recent, plus slight boost to cold numbers for diversity
            w[n] = 0.5 * (overall[n] + 1) + 0.5 * (recent[n] + 1)
            if n in cold_set:
                w[n] *= 1.15
    # apply number_scores as multiplier
    for n in range(1, 46):
        w[n] *= (0.5 + number_scores.get(n, 0.5))
    return w


def _sample_one(weights, include, exclude, rng):
    include = set(include or [])
    exclude = set(exclude or [])
    pool = [n for n in range(1, 46) if n not in exclude and n not in include]
    chosen = set(include)
    # number to pick
    k = config.NUMBERS_PER_DRAW - len(include)
    # weighted sampling without replacement
    avail = list(pool)
    w = [weights[n] for n in avail]
    for _ in range(k):
        if not avail:
            break
        total = sum(w)
        if total <= 0:
            idx = rng.randrange(len(avail))
        else:
            r = rng.random() * total
            acc = 0.0
            idx = len(avail) - 1
            for i, val in enumerate(w):
                acc += val
                if r <= acc:
                    idx = i
                    break
        chosen.add(avail.pop(idx))
        w.pop(idx)
    return sorted(chosen)


def generate_sets(draws: List[Draw], n_sets: int = config.DEFAULT_SETS,
                  strategy: str = config.DEFAULT_STRATEGY,
                  include: Optional[List[int]] = None,
                  exclude: Optional[List[int]] = None,
                  seed: Optional[int] = None,
                  anti_popular: bool = False,
                  progress_cb: Optional[Callable] = None) -> List[Dict]:
    rng = random.Random(seed if seed is not None else int(time.time() * 1000))
    include = list(include or [])
    exclude = list(exclude or [])
    number_scores = S.number_scores(draws) if draws else {n: 0.5 for n in range(1, 46)}
    weights = _weights(strategy, draws, number_scores)

    draw_stats = None
    if draws:
        sums = [S.sum_of(d.numbers) for d in draws]
        acs = [S.ac_of(d.numbers) for d in draws]
        mean_sum = sum(sums) / len(sums)
        std_sum = (sum((x - mean_sum) ** 2 for x in sums) / len(sums)) ** 0.5 or 1
        mean_ac = sum(acs) / len(acs)
        std_ac = (sum((x - mean_ac) ** 2 for x in acs) / len(acs)) ** 0.5 or 1
        draw_stats = (mean_sum, std_sum, mean_ac, std_ac)

    pool_size = 600
    candidates = []
    attempts = 0
    max_attempts = 15000
    while len(candidates) < pool_size and attempts < max_attempts:
        attempts += 1
        combo = _sample_one(weights, include, exclude, rng)
        if len(combo) != config.NUMBERS_PER_DRAW:
            continue
        if not F.is_valid(combo, include=include, exclude=exclude):
            continue
        candidates.append(combo)
        if progress_cb and len(candidates) % 500 == 0:
            try:
                progress_cb(len(candidates), pool_size)
            except Exception:
                pass

    if not candidates:
        # relax: generate random valid combos
        attempts2 = 0
        while len(candidates) < 100 and attempts2 < 50000:
            attempts2 += 1
            combo = sorted(rng.sample(range(1, 46), 6))
            if include and not set(include).issubset(set(combo)):
                continue
            if exclude and (set(combo) & set(exclude)):
                continue
            if not F.is_valid(combo, include=include, exclude=exclude):
                continue
            candidates.append(combo)

    # 중복 조합 제거 → 서로 다른 고유 조합만 (N세트 = N개 조합, 낭비 없음)
    seen = set()
    uniq = []
    for c in candidates:
        t = tuple(c)
        if t not in seen:
            seen.add(t)
            uniq.append(c)
    candidates = uniq

    # score
    scored = SC.rank_candidates(candidates, number_scores, draw_stats,
                                anti_popular=anti_popular)

    # greedy diverse selection
    selected = []
    selected_sets = []
    # penalty lambda
    LAMBDA = 0.15
    remaining = list(scored)
    for _ in range(n_sets):
        if not remaining:
            break
        best_idx = 0
        best_val = None
        for i, (sc, combo) in enumerate(remaining):
            # diversity penalty
            overlap_pen = 0
            for s in selected_sets:
                overlap_pen = max(overlap_pen, len(set(combo) & set(s)))
            adj = sc - LAMBDA * overlap_pen
            if best_val is None or adj > best_val:
                best_val = adj
                best_idx = i
        sc, combo = remaining.pop(best_idx)
        selected_sets.append(combo)
        # build result dict
        result = {
            "numbers": list(combo),
            "score": round(float(sc), 4),
            "sum": S.sum_of(combo),
            "odd_count": S.odd_count(combo),
            "ac": S.ac_of(combo),
            "consecutive_pairs": S.consecutive_pairs(combo),
            "zone_counts": S.zone_counts(combo),
            "strategy": strategy,
        }
        selected.append(result)

    return selected
