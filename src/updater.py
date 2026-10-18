"""Automatic update of lotto draw data."""

import threading
import time
import datetime
from typing import Callable, Optional

from .data import storage, fetcher
from . import config


class Updater:
    def __init__(self, progress_cb: Optional[Callable] = None, log_cb: Optional[Callable] = None):
        self.progress_cb = progress_cb
        self.log_cb = log_cb
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def _log(self, msg):
        if self.log_cb:
            try:
                self.log_cb(msg)
            except Exception:
                pass

    def seed_if_empty(self):
        """If DB empty, seed from mirror (fast)."""
        if storage.count_draws() == 0:
            self._log("DB empty. Seeding from mirror (all history)...")
            try:
                draws = fetcher.seed_from_mirror()
                storage.upsert_draws(draws)
                storage.export_json()
                self._log(f"Seeded {len(draws)} draws.")
            except Exception as e:
                self._log(f"Seed failed: {e}. Trying API range...")
                # fallback: fetch from API 1..latest
                try:
                    lr = fetcher.fetch_latest_round_no()
                    if lr:
                        draws = fetcher.fetch_range(1, lr, sleep=0.2)
                        storage.upsert_draws(draws)
                        storage.export_json()
                        self._log(f"Seeded {len(draws)} draws via API.")
                except Exception as e2:
                    self._log(f"API seed failed: {e2}")

    def update_now(self) -> int:
        """Fetch new draws since last stored. Returns count added.

        Re-entrant calls are rejected while another update is running so the
        background thread and the manual-update button cannot overlap.
        """
        if not self._lock.acquire(blocking=False):
            self._log("Update already in progress; skipping.")
            return 0
        try:
            return self._update_locked()
        finally:
            self._lock.release()

    def _update_locked(self) -> int:
        storage.init_db()
        self.seed_if_empty()
        latest_local = storage.get_latest_round() or 0
        try:
            latest_remote = fetcher.fetch_latest_round_no()
        except Exception as e:
            self._log(f"Could not get latest round: {e}")
            return 0
        if latest_remote is None:
            self._log("Remote latest unknown.")
            return 0
        if latest_remote <= latest_local:
            self._log(f"Already up to date (local {latest_local}, remote {latest_remote}).")
            return 0
        self._log(f"Updating rounds {latest_local + 1}..{latest_remote} ...")
        added = 0
        new_draws = []
        for r in range(latest_local + 1, latest_remote + 1):
            d = fetcher.fetch_one(r)
            if d is not None:
                new_draws.append(d)
                added += 1
            if self.progress_cb:
                try:
                    self.progress_cb(r, latest_remote, d is not None)
                except Exception:
                    pass
            time.sleep(0.25)
        if new_draws:
            storage.upsert_draws(new_draws)
            storage.export_json()
        self._log(f"Added {added} new draws. Latest now {storage.get_latest_round()}.")
        return added

    def start_background(self, interval_hours: float = 6.0):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def loop():
            while not self._stop.is_set():
                try:
                    self.update_now()
                except Exception as e:
                    self._log(f"Background update error: {e}")
                # sleep interval (check stop every 1 sec for quick exit)
                for _ in range(int(interval_hours * 3600)):
                    if self._stop.is_set():
                        break
                    time.sleep(1)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
