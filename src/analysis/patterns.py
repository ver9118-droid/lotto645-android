"""Pattern/hard-constraint validation for 6-number combinations."""

from . import stats as S
from .. import config


def passes_constraints(nums) -> bool:
    nums = sorted(nums)
    s = S.sum_of(nums)
    if not (config.SUM_MIN <= s <= config.SUM_MAX):
        return False
    ac = S.ac_of(nums)
    if not (config.AC_MIN <= ac <= config.AC_MAX):
        return False
    oc = S.odd_count(nums)
    if oc not in config.ODD_COUNTS_ALLOWED:
        return False
    hc = S.high_count(nums)
    if hc not in config.HIGH_COUNTS_ALLOWED:
        return False
    cp = S.consecutive_pairs(nums)
    if cp > config.MAX_CONSECUTIVE_PAIRS:
        return False
    zc = S.zone_counts(nums)
    distinct = sum(1 for c in zc if c > 0)
    if distinct < config.MIN_DISTINCT_ZONES:
        return False
    # no duplicate
    if len(set(nums)) != len(nums):
        return False
    # range
    if any(n < config.LOTTO_MIN or n > config.LOTTO_MAX for n in nums):
        return False
    return True
