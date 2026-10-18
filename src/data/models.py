"""Data models for lotto draws."""

from dataclasses import dataclass, field
from typing import List, Optional
import json


@dataclass
class Draw:
    round: int
    date: str  # YYYY-MM-DD
    numbers: List[int]
    bonus: int
    first_prize: int = 0
    first_winners: int = 0
    total_sales: int = 0

    def __post_init__(self):
        self.numbers = sorted(self.numbers)

    @property
    def main_set(self):
        return set(self.numbers)

    def to_dict(self):
        return {
            "round": self.round,
            "date": self.date,
            "numbers": list(self.numbers),
            "bonus": self.bonus,
            "first_prize": self.first_prize,
            "first_winners": self.first_winners,
            "total_sales": self.total_sales,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            round=d["round"],
            date=d["date"],
            numbers=list(d["numbers"]),
            bonus=d["bonus"],
            first_prize=d.get("first_prize", 0),
            first_winners=d.get("first_winners", 0),
            total_sales=d.get("total_sales", 0),
        )

    @classmethod
    def from_dhlottery(cls, item):
        nums = [item[f"tm{i}WnNo"] for i in range(1, 7)]
        raw_date = item["ltRflYmd"]
        date = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        return cls(
            round=item["ltEpsd"],
            date=date,
            numbers=nums,
            bonus=item["bnsWnNo"],
            first_prize=item.get("rnk1WnAmt", 0),
            first_winners=item.get("rnk1WnNope", 0),
            total_sales=item.get("wholEpsdSumNtslAmt", 0),
        )

    @classmethod
    def from_mirror(cls, item):
        nums = list(item["numbers"])
        date = item["date"][:10]
        divs = item.get("divisions", []) or []
        first_prize = divs[0].get("prize", 0) if divs else 0
        first_winners = divs[0].get("winners", 0) if divs else 0
        return cls(
            round=item["draw_no"],
            date=date,
            numbers=nums,
            bonus=item["bonus_no"],
            first_prize=first_prize,
            first_winners=first_winners,
            total_sales=item.get("total_sales_amount", 0),
        )
