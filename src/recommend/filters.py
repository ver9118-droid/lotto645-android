"""Constraint filters for candidate combinations."""

from ..analysis import patterns as P


def filter_candidates(nums_list, include=None, exclude=None):
    include = set(include or [])
    exclude = set(exclude or [])
    out = []
    for nums in nums_list:
        s = set(nums)
        if include and not include.issubset(s):
            continue
        if exclude and (s & exclude):
            continue
        if not P.passes_constraints(nums):
            continue
        out.append(sorted(nums))
    return out


def is_valid(nums, include=None, exclude=None):
    include = set(include or [])
    exclude = set(exclude or [])
    s = set(nums)
    if include and not include.issubset(s):
        return False
    if exclude and (s & exclude):
        return False
    return P.passes_constraints(nums)
