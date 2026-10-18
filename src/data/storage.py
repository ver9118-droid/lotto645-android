"""Persistent storage for lotto draws (SQLite + JSON)."""

import sqlite3
import json
import os
import threading
from typing import List, Optional
from .models import Draw
from .. import config

_lock = threading.RLock()


def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS draws (
                    round INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    n1 INTEGER, n2 INTEGER, n3 INTEGER, n4 INTEGER, n5 INTEGER, n6 INTEGER,
                    bonus INTEGER NOT NULL,
                    first_prize INTEGER DEFAULT 0,
                    first_winners INTEGER DEFAULT 0,
                    total_sales INTEGER DEFAULT 0
                )"""
            )
            conn.commit()
        finally:
            conn.close()


def upsert_draws(draws: List[Draw]):
    with _lock:
        conn = _connect()
        try:
            for d in draws:
                nums = sorted(d.numbers)
                conn.execute(
                    """INSERT INTO draws(round,date,n1,n2,n3,n4,n5,n6,bonus,first_prize,first_winners,total_sales)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(round) DO UPDATE SET
                         date=excluded.date, n1=excluded.n1, n2=excluded.n2, n3=excluded.n3,
                         n4=excluded.n4, n5=excluded.n5, n6=excluded.n6, bonus=excluded.bonus,
                         first_prize=excluded.first_prize, first_winners=excluded.first_winners,
                         total_sales=excluded.total_sales""",
                    (d.round, d.date, *nums, d.bonus, d.first_prize, d.first_winners, d.total_sales),
                )
            conn.commit()
        finally:
            conn.close()


def get_all_draws() -> List[Draw]:
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute("SELECT * FROM draws ORDER BY round ASC").fetchall()
            out = []
            for r in rows:
                nums = [r[f"n{i}"] for i in range(1, 7)]
                out.append(Draw(
                    round=r["round"], date=r["date"], numbers=nums, bonus=r["bonus"],
                    first_prize=r["first_prize"], first_winners=r["first_winners"],
                    total_sales=r["total_sales"],
                ))
            return out
        finally:
            conn.close()


def get_latest_round() -> Optional[int]:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT MAX(round) AS m FROM draws").fetchone()
            return row["m"] if row and row["m"] is not None else None
        finally:
            conn.close()


def count_draws() -> int:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT COUNT(*) AS c FROM draws").fetchone()
            return row["c"]
        finally:
            conn.close()


def export_json(path: Optional[str] = None):
    path = path or config.DRAWS_JSON_PATH
    draws = get_all_draws()
    with open(path, "w", encoding="utf-8") as f:
        json.dump([d.to_dict() for d in draws], f, ensure_ascii=False, indent=2)


def import_json(path: Optional[str] = None) -> int:
    path = path or config.DRAWS_JSON_PATH
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    draws = [Draw.from_dict(d) for d in data]
    upsert_draws(draws)
    return len(draws)
