"""Scoring candidate combinations."""

import math

from ..analysis import stats as S


def pattern_fit_score(nums, draw_stats) -> float:
    """How close the combination's stats are to historical means (0..1)."""
    if not draw_stats:
        return 0.5
    nums = sorted(nums)
    mean_sum, std_sum, mean_ac, std_ac = draw_stats
    z_sum = abs(S.sum_of(nums) - mean_sum) / std_sum
    z_ac = abs(S.ac_of(nums) - mean_ac) / std_ac
    fit = math.exp(-(z_sum * z_sum + z_ac * z_ac) / 4.0)
    return fit


def popularity_penalty(nums) -> float:
    """인기(많이 선택되는) 패턴일수록 큰 페널티.

    실데이터 분석: 12이하 번호가 많을수록, 합계가 낮을수록
    '판매액 대비 1등 당첨자수'(=인기도)가 높았다.
    (12이하 개수 3개 이상 → 1개 이하로 바꾸면 공동당첨 위험 약 13% 감소)
    """
    low12 = sum(1 for n in nums if n <= 12)
    low31 = sum(1 for n in nums if n <= 31)
    pen = 0.03 * low12 + 0.005 * low31
    if S.sum_of(nums) < 130:
        pen += 0.02
    return pen


def score_candidate(nums, number_scores, draw_stats, anti_popular=False) -> float:
    nums = sorted(nums)
    ns = sum(number_scores.get(n, 0.5) for n in nums) / 6.0
    pf = pattern_fit_score(nums, draw_stats)
    zc = S.zone_counts(nums)
    distinct_zones = sum(1 for c in zc if c > 0)
    zone_bonus = distinct_zones / 5.0
    score = 0.45 * ns + 0.35 * pf + 0.20 * zone_bonus
    if anti_popular:
        score -= popularity_penalty(nums)
    return score


def rank_candidates(candidates, number_scores, draw_stats, anti_popular=False):
    scored = [(score_candidate(c, number_scores, draw_stats, anti_popular), c)
              for c in candidates]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored
