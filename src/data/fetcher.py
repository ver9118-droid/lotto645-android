"""Fetching lotto draw data from dhlottery (new API) and mirror fallback.

모바일(Android) 빌드용 사본입니다.
외부 패키지(requests) 없이 **표준 라이브러리만** 사용합니다.
(p4a 빌드에서 순수 파이썬 패키지 설치가 실패하는 문제를 근본적으로 제거하고,
 APK 용량도 줄입니다. HTTPS 인증서는 앱에 포함한 CA 번들로 검증합니다.)
"""

import gzip
import json
import os
import ssl
import time
import datetime
import urllib.parse
import urllib.request
from typing import List, Optional

from .models import Draw
from .. import config

SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.dhlottery.co.kr/lt645/result",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

_SSL_CTX = None


def _ssl_context():
    """HTTPS 인증서 검증 컨텍스트. 앱에 포함된 CA 번들을 우선 사용."""
    global _SSL_CTX
    if _SSL_CTX is not None:
        return _SSL_CTX
    cafile = getattr(config, "CA_BUNDLE_PATH", None)
    try:
        if cafile and os.path.exists(cafile):
            _SSL_CTX = ssl.create_default_context(cafile=cafile)
        else:
            _SSL_CTX = ssl.create_default_context()
    except Exception:
        _SSL_CTX = ssl.create_default_context()
    return _SSL_CTX


class _Resp:
    """requests.Response 최소 호환 객체."""

    def __init__(self, status_code, body: bytes, headers=None):
        self.status_code = status_code
        self.content = body
        self.headers = headers or {}
        self.text = body.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text)


def _get(url, params=None, timeout=20, retries=3):
    last = None
    if params:
        sep = "&" if "?" in url else "?"
        url = url + sep + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=SESSION_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=_ssl_context()) as fp:
                body = fp.read()
                enc = (fp.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    body = gzip.decompress(body)
                r = _Resp(getattr(fp, "status", 200), body, dict(fp.headers))
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
