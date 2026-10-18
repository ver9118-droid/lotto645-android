"""Statistical analysis of lotto draws."""

from collections import Counter, defaultdict
from typing import List, Dict, Tuple
import math

from .. import config
from ..data.models import Draw


def ac_of(nums) -> int:
    """Arithmetic Complexity of a 6-number combination."""
    nums = sorted(nums)
    diffs = set()
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            diffs.add(abs(nums[i] - nums[j]))
    return len(diffs) - 5  # 5 = (6 choose 2?) standard: unique diffs count - (n-1)?? 
    # Standard AC = (number of distinct differences) - (n-1) where n=6 => -5. Yes.


def frequency(draws: List[Draw]) -> List[int]:
    counts = [0] * (config.LOTTO_MAX + 1)
    for d in draws:
        for n in d.numbers:
            counts[n] += 1
    return counts  # index 1..45


def bonus_frequency(draws: List[Draw]) -> List[int]:
    counts = [0] * (config.LOTTO_MAX + 1)
    for d in draws:
        counts[d.bonus] += 1
    return counts


def recent_frequency(draws: List[Draw], window: int = config.RECENT_WINDOW) -> List[int]:
    recent = draws[-window:] if len(draws) >= window else draws
    return frequency(recent)


def odd_count(nums) -> int:
    return sum(1 for n in nums if n % 2 == 1)


def high_count(nums) -> int:
    # high = 23..45
    return sum(1 for n in nums if n >= 23)


def zone_counts(nums) -> List[int]:
    out = [0] * len(config.ZONES)
    for n in nums:
        for i, (lo, hi) in enumerate(config.ZONES):
            if lo <= n <= hi:
                out[i] += 1
                break
    return out


def consecutive_pairs(nums) -> int:
    s = sorted(nums)
    c = 0
    for i in range(len(s) - 1):
        if s[i + 1] == s[i] + 1:
            c += 1
    return c


def sum_of(nums) -> int:
    return sum(nums)


def odd_even_distribution(draws: List[Draw]) -> Dict[int, int]:
    c = Counter()
    for d in draws:
        c[odd_count(d.numbers)] += 1
    return dict(sorted(c.items()))


def high_low_distribution(draws: List[Draw]) -> Dict[int, int]:
    c = Counter()
    for d in draws:
        c[high_count(d.numbers)] += 1
    return dict(sorted(c.items()))


def sum_distribution(draws: List[Draw], bucket: int = 10) -> Dict[str, int]:
    c = Counter()
    for d in draws:
        s = sum_of(d.numbers)
        key = f"{(s // bucket) * bucket}-{(s // bucket) * bucket + bucket - 1}"
        c[key] += 1
    return dict(sorted(c.items()))


def ac_distribution(draws: List[Draw]) -> Dict[int, int]:
    c = Counter()
    for d in draws:
        c[ac_of(d.numbers)] += 1
    return dict(sorted(c.items()))


def zone_distribution(draws: List[Draw]) -> Dict[str, int]:
    # average counts per zone
    totals = [0] * len(config.ZONES)
    for d in draws:
        zc = zone_counts(d.numbers)
        for i in range(len(config.ZONES)):
            totals[i] += zc[i]
    n = len(draws) or 1
    return {f"{lo}-{hi}": round(totals[i] / n, 3) for i, (lo, hi) in enumerate(config.ZONES)}


def last_digit_frequency(draws: List[Draw]) -> List[int]:
    counts = [0] * 10
    for d in draws:
        for n in d.numbers:
            counts[n % 10] += 1
    return counts


def pair_frequency(draws: List[Draw], top: int = 20) -> List[Tuple[Tuple[int, int], int]]:
    c = Counter()
    for d in draws:
        nums = sorted(d.numbers)
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                c[(nums[i], nums[j])] += 1
    return c.most_common(top)


def hot_numbers(draws: List[Draw], window: int = config.HOT_COLD_WINDOW, top: int = 15) -> List[int]:
    rf = recent_frequency(draws, window)
    # numbers sorted by recent freq desc, then overall freq desc
    overall = frequency(draws)
    order = sorted(range(1, 46), key=lambda n: (rf[n], overall[n]), reverse=True)
    return order[:top]


def cold_numbers(draws: List[Draw], window: int = config.HOT_COLD_WINDOW, top: int = 15) -> List[int]:
    rf = recent_frequency(draws, window)
    overall = frequency(draws)
    # cold = low recent freq; tie-break by overall freq asc
    order = sorted(range(1, 46), key=lambda n: (rf[n], overall[n]))
    return order[:top]


def number_scores(draws: List[Draw]) -> Dict[int, float]:
    """Composite score per number (0..1) combining overall freq and recent momentum."""
    if not draws:
        return {n: 0.5 for n in range(1, 46)}
    overall = frequency(draws)
    recent = recent_frequency(draws, config.RECENT_WINDOW)
    max_o = max(overall[1:]) or 1
    max_r = max(recent[1:]) or 1
    min_o = min(overall[1:])
    # normalize overall to 0..1
    out = {}
    for n in range(1, 46):
        o = (overall[n] - min_o) / (max_o - min_o + 1e-9)
        r = recent[n] / (max_r + 1e-9)
        # momentum: recent vs expected
        expected_recent = (len(draws[-config.RECENT_WINDOW:]) if draws else 1) * 6 / 45
        momentum = (recent[n] - expected_recent) / (expected_recent + 1e-9)
        momentum = max(-1.0, min(1.0, momentum))
        out[n] = 0.4 * o + 0.35 * r + 0.25 * (momentum + 1) / 2
    return out


def consecutive_distribution(draws):
    c = Counter()
    for d in draws:
        c[consecutive_pairs(d.numbers)] += 1
    return dict(sorted(c.items()))


def summary(draws: List[Draw]) -> dict:
    if not draws:
        return {}
    sums = [sum_of(d.numbers) for d in draws]
    acs = [ac_of(d.numbers) for d in draws]
    ods = [odd_count(d.numbers) for d in draws]
    return {
        "total_draws": len(draws),
        "first_round": draws[0].round,
        "last_round": draws[-1].round,
        "last_date": draws[-1].date,
        "avg_sum": round(sum(sums) / len(sums), 2),
        "min_sum": min(sums),
        "max_sum": max(sums),
        "avg_ac": round(sum(acs) / len(acs), 2),
        "avg_odd": round(sum(ods) / len(ods), 2),
        "most_common_odd": Counter(ods).most_common(1)[0],
    }
