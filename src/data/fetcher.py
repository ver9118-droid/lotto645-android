"""Fetching lotto draw data from dhlottery (new API) and mirror fallback."""

import time
import datetime
import requests
from typing import List, Optional

from .models import Draw
from .. import config

SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.dhlottery.co.kr/lt645/result",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def _get(url, params=None, timeout=20, retries=3):
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=SESSION_HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r
            last = Exception(f"HTTP {r.status_code}")
        except Exception as e:
            last = e
        time.sleep(1 + attempt)
    raise last if last else Exception("request failed")


def fetch_one(round_no: int) -> Optional[Draw]:
    """Fetch a single draw. Returns None if not yet drawn / invalid."""
    ts = int(time.time() * 1000)
    params = {"srchLtEpsd": round_no, "_": ts}
    try:
        r = _get(config.DHLOTTERY_DETAIL_URL, params=params)
        data = r.json()
    except Exception:
        return None
    lst = (data.get("data") or {}).get("list") or []
    if not lst:
        return None
    item = None
    for e in lst:
        if e.get("ltEpsd") == round_no:
            item = e
            break
    if item is None:
        item = lst[0]
    if item.get("ltEpsd") != round_no:
        return None
    try:
        return Draw.from_dhlottery(item)
    except Exception:
        return None


def fetch_latest_round_no() -> Optional[int]:
    # Try mirror first
    try:
        r = _get(config.MIRROR_LATEST_URL, timeout=15)
        d = r.json()
        if "draw_no" in d:
            return int(d["draw_no"])
    except Exception:
        pass
    # Estimate from calendar
    start = datetime.date(2002, 12, 7)
    today = datetime.date.today()
    weeks = (today - start).days // 7 + 1
    est = weeks + 1
    for r in range(est + 3, est - 5, -1):
        if r < 1:
            continue
        d = fetch_one(r)
        if d is not None:
            return r
    return None


def seed_from_mirror() -> List[Draw]:
    """Download all historical draws from mirror. Returns list."""
    r = _get(config.MIRROR_ALL_URL, timeout=60)
    data = r.json()
    draws = []
    for item in data:
        try:
            draws.append(Draw.from_mirror(item))
        except Exception:
            continue
    return draws


def fetch_range(start_round: int, end_round: int, sleep: float = 0.3, progress_cb=None) -> List[Draw]:
    out = []
    for r in range(start_round, end_round + 1):
        d = fetch_one(r)
        if d is not None:
            out.append(d)
        if progress_cb:
            try:
                progress_cb(r, end_round, d is not None)
            except Exception:
                pass
        time.sleep(sleep)
    return out
