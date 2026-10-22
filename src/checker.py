"""당첨 확인 로직: 번호 파싱(수동/QR 텍스트) + 등급 판정.

- parse_tickets(): 텍스트에서 6개짜리 번호 묶음을 추출 (줄마다 1티켓, 한 줄에 여러 개 가능)
- check_numbers(): 1~5등 판정 및 당첨금 계산
"""

import re
from typing import Dict, List, Optional, Sequence

# 등급별 고정 당첨금 (4~5등은 회차와 무관하게 고정)
FIXED_PRIZES = {4: 50_000, 5: 5_000}

RANK_LABELS = {
    1: "1등",
    2: "2등",
    3: "3등",
    4: "4등",
    5: "5등",
    0: "미당첨",
}

# 숫자 토큰: 1~2자리, 다른 숫자에 붙어있지 않아야 함 (4자리 회차/연도 등은 제외)
_NUM_RE = re.compile(r"(?<![\d.])\d{1,2}(?![\d])")

# 파싱 전에 제거할 패턴 (날짜/시간/회차/큰 숫자 등 → 번호로 오인 방지)
_STRIP_PATTERNS = [
    re.compile(r"\d{4}\s*[-./]\s*\d{1,2}\s*[-./]\s*\d{1,2}"),   # 2026-10-22
    re.compile(r"\d{1,2}\s*:\s*\d{2}"),                           # 21:00
    re.compile(r"\d{1,3}(?:,\d{3})+"),                            # 8,145,060
    re.compile(r"\d+\s*회"),                                      # 1201회
    re.compile(r"\d+\s*:\s*\d+\s*"),                              # 12:30:00
    re.compile(r"https?://\S+"),                                  # URL
]

# 토큰 사이를 이어줄 수 있는 구분 문자 ('.' 은 구분자가 아님 → "1. 01 07 ..." 처리)
_SEP_CHARS = set(" \t,，、;:/·-–—_+")


def _normalize(text: str) -> str:
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    for pat in _STRIP_PATTERNS:
        s = pat.sub(" ", s)
    return s


def _clusters(line: str) -> List[List[int]]:
    """한 줄에서 '구분자로 이어진 숫자 덩어리' 단위로 나누어 숫자 목록 반환."""
    toks = [(m.group(), m.start(), m.end()) for m in _NUM_RE.finditer(line)]
    out: List[List[int]] = []
    cur: List[int] = []
    prev_end = None
    for raw, st, en in toks:
        if prev_end is not None:
            gap = line[prev_end:st]
            if gap and all(ch in _SEP_CHARS for ch in gap):
                cur.append(int(raw))
            else:
                if cur:
                    out.append(cur)
                cur = [int(raw)]
        else:
            cur = [int(raw)]
        prev_end = en
    if cur:
        out.append(cur)
    return out


def parse_tickets(text: str) -> List[List[int]]:
    """텍스트(QR 내용물/직접 입력)에서 번호 6개짜리 티켓 목록 추출.

    - 줄 단위로 처리: 한 줄 = 한 티켓(또는 한 줄에 여러 티켓)
    - 1~45 범위 숫자만 사용, 중복 번호가 있는 묶음은 무시
    """
    tickets: List[List[int]] = []
    seen = set()
    for raw_line in _normalize(text or "").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        for cluster in _clusters(line):
            vals = [v for v in cluster if 1 <= v <= 45]
            if not vals:
                continue
            # 6개 단위로 분할 (남는 숫자는 버림)
            for i in range(0, len(vals) - len(vals) % 6, 6):
                chunk = vals[i:i + 6]
                if len(chunk) != 6 or len(set(chunk)) != 6:
                    continue
                key = tuple(sorted(chunk))
                if key in seen:
                    continue
                seen.add(key)
                tickets.append(list(key))
    return tickets


def check_numbers(numbers: Sequence[int], draw, prizes: Optional[Dict[int, int]] = None) -> Dict:
    """1티켓의 당첨 여부 판정.

    draw: src.data.models.Draw (numbers/bonus 필요)
    prizes: {등급: 1인당 당첨금} (없으면 4·5등 고정 금액만 사용)
    """
    ticket = sorted(set(int(n) for n in numbers))
    winning = set(int(n) for n in draw.numbers)
    bonus = int(draw.bonus)
    matched = len(set(ticket) & winning)
    has_bonus = bonus in ticket

    if matched == 6:
        rank = 1
    elif matched == 5 and has_bonus:
        rank = 2
    elif matched == 5:
        rank = 3
    elif matched == 4:
        rank = 4
    elif matched == 3:
        rank = 5
    else:
        rank = 0

    prize = 0
    if rank:
        if prizes and rank in prizes and prizes.get(rank):
            prize = int(prizes[rank])
        else:
            prize = FIXED_PRIZES.get(rank, 0)

    return {
        "numbers": ticket,
        "rank": rank,
        "rank_label": RANK_LABELS.get(rank, "미당첨"),
        "matched": matched,
        "bonus": bonus,
        "has_bonus": has_bonus,
        "prize": prize,
        "detail": _detail_text(rank, matched, has_bonus),
    }


def _detail_text(rank: int, matched: int, has_bonus: bool) -> str:
    if rank == 1:
        return "6개 모두 일치"
    if rank == 2:
        return "5개 일치 + 보너스"
    if rank == 3:
        return "5개 일치"
    if rank == 4:
        return "4개 일치"
    if rank == 5:
        return "3개 일치"
    return f"{matched}개 일치"


def format_prize(amount: int) -> str:
    """금액을 '1,234,567원' 형태로."""
    return f"{int(amount):,}원"


def summarize(results: List[Dict]) -> Dict:
    """검사 결과 요약(총 당첨금, 등급별 개수)."""
    total = sum(r.get("prize", 0) for r in results)
    counts = {}
    for r in results:
        if r.get("rank"):
            counts[r["rank"]] = counts.get(r["rank"], 0) + 1
    return {
        "total_prize": total,
        "total_prize_text": format_prize(total),
        "counts": counts,
        "winners": sum(counts.values()),
        "tickets": len(results),
    }
