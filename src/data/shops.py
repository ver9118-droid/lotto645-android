"""당첨 판매점 조회(동행복권) + 지오코딩(Nominatim) + 거리 계산.

모바일(Android) 빌드용 사본입니다.
외부 패키지(requests) 없이 **표준 라이브러리만** 사용합니다.
(앱에 포함된 CA 번들로 HTTPS 인증서를 검증합니다.)
"""

import gzip
import json
import math
import ssl
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from .. import config

SHOP_URL = "https://www.dhlottery.co.kr/wnprchsplcsrch/selectLtWnShp.do"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

_SHOP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.dhlottery.co.kr/wnprchsplcsrch/home",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

_GEO_HEADERS = {
    "User-Agent": "KoreanLottoApp/1.1 (Android)",
    "Accept-Language": "ko",
}

_SSL_CTX = None
_last_geo_call = [0.0]


def _ssl_context():
    global _SSL_CTX
    if _SSL_CTX is not None:
        return _SSL_CTX
    cafile = getattr(config, "CA_BUNDLE_PATH", None)
    try:
        if cafile:
            import os
            if os.path.exists(cafile):
                _SSL_CTX = ssl.create_default_context(cafile=cafile)
            else:
                _SSL_CTX = ssl.create_default_context()
        else:
            _SSL_CTX = ssl.create_default_context()
    except Exception:
        _SSL_CTX = ssl.create_default_context()
    return _SSL_CTX


def _get_json(url, params=None, headers=None, timeout=20, retries=2):
    """표준 라이브러리로 JSON GET."""
    if params:
        sep = "&" if "?" in url else "?"
        url = url + sep + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers or _SHOP_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=_ssl_context()) as fp:
                body = fp.read()
                enc = (fp.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    body = gzip.decompress(body)
            return json.loads(body.decode("utf-8", errors="replace"))
        except Exception as e:
            last = e
        time.sleep(0.8 + attempt)
    raise last if last else Exception("request failed")


def fetch_winning_shops(round_no: int, rank: int = 1, region: str = "",
                        include_online: bool = False) -> List[Dict]:
    """특정 회차의 당첨 판매점 목록 조회.

    rank: 1 → 1등 당첨매장, 2 → 2등, 0 → 전체
    """
    params = {
        "srchWnShpRnk": str(rank) if rank else "",
        "srchLtEpsd": str(round_no),
        "srchShpLctn": region or "",
    }
    data = _get_json(SHOP_URL, params=params)
    payload = (data or {}).get("data") or {}
    items = payload.get("list") or []

    shops: List[Dict] = []
    for it in items:
        name = (it.get("shpNm") or it.get("tradNm") or "").strip()
        if not include_online and ("인터넷" in name or "온라인" in name):
            continue
        try:
            lat = float(it.get("shpLat"))
            lon = float(it.get("shpLot"))
        except (TypeError, ValueError):
            continue
        if lat == 0 and lon == 0:
            continue
        addr = (it.get("shpAddr") or it.get("befAddr") or it.get("rdnm") or "").strip()
        shops.append({
            "name": name,
            "address": addr,
            "tel": (it.get("shpTelno") or "").strip(),
            "lat": lat,
            "lon": lon,
            "combo": (it.get("atmtPsvYnTxt") or "").strip(),
            "rank": it.get("wnShpRnk") or rank,
            "region": (it.get("region") or "").strip(),
        })
    return shops


def geocode(query: str) -> Optional[Dict]:
    """주소/지명 → 좌표 변환 (Nominatim). 실패 시 None."""
    q = (query or "").strip()
    if not q:
        return None
    wait = 1.0 - (time.time() - _last_geo_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_geo_call[0] = time.time()
    data = _get_json(NOMINATIM_URL,
                     params={"q": q, "format": "json", "limit": 1,
                             "accept-language": "ko"},
                     headers=_GEO_HEADERS, timeout=20)
    if not data:
        return None
    item = data[0]
    try:
        lat = float(item["lat"])
        lon = float(item["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "lat": lat,
        "lon": lon,
        "label": item.get("display_name") or q,
        "short": _short_label(item, q),
    }


def _short_label(item: Dict, fallback: str) -> str:
    for key in ("name", "display_name"):
        v = item.get(key)
        if v:
            return str(v).split(",")[0].strip() or fallback
    return fallback


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 사이 거리(km)."""
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def sort_by_distance(shops: List[Dict], lat: float, lon: float,
                     radius_km: Optional[float] = None) -> List[Dict]:
    """기준 좌표로부터 거리 계산 + 정렬(가까운 순)."""
    out = []
    for s in shops:
        d = haversine(lat, lon, s["lat"], s["lon"])
        if radius_km and d > radius_km:
            continue
        item = dict(s)
        item["distance_km"] = d
        out.append(item)
    out.sort(key=lambda x: x["distance_km"])
    return out


def format_distance(km: float) -> str:
    if km < 1:
        return f"{int(round(km * 1000))}m"
    if km < 10:
        return f"{km:.1f}km"
    return f"{int(round(km))}km"
