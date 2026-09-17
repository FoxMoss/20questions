import sqlite3
import threading
import time
from collections import deque


class GameLimiter:
    """Thread-safe games-per-IP limiter (sliding window).

    In-memory by default. Pass ``path`` to share state across gunicorn
    workers/processes via SQLite (file-backed). All operations are serialized
    by a lock, so any number of threads is safe; SQLite's file locking makes
    it safe across processes too.
    """

    def __init__(
        self,
        max_games: int = 10,
        window_seconds: int = 24 * 3600,
        path: str | None = None,
    ):
        self.max_games = max_games
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._db = None
        self._mem: dict[str, deque[float]] = {}
        if path is not None:
            self._db = sqlite3.connect(
                path, check_same_thread=False, isolation_level=None
            )
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA busy_timeout=5000")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS games (ip TEXT NOT NULL, ts REAL NOT NULL)"
            )
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_games ON games (ip, ts)"
            )

    def _prune_mem(self, ip: str, cutoff: float) -> deque[float]:
        history = self._mem.setdefault(ip, deque())
        while history and history[0] < cutoff:
            history.popleft()
        return history

    def _db_write(self, ip: str, now: float, cutoff: float) -> bool:
        """Atomic check-and-record; returns False when the limit is hit."""
        self._db.execute("BEGIN IMMEDIATE")
        try:
            self._db.execute("DELETE FROM games WHERE ts < ?", (cutoff,))
            (used,) = self._db.execute(
                "SELECT COUNT(*) FROM games WHERE ip = ?", (ip,)
            ).fetchone()
            if used >= self.max_games:
                self._db.execute("ROLLBACK")
                return False
            self._db.execute(
                "INSERT INTO games (ip, ts) VALUES (?, ?)", (ip, now)
            )
            self._db.execute("COMMIT")
            return True
        except sqlite3.Error:
            self._db.execute("ROLLBACK")
            raise

    def _db_count(self, ip: str, cutoff: float) -> int:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            self._db.execute("DELETE FROM games WHERE ts < ?", (cutoff,))
            (used,) = self._db.execute(
                "SELECT COUNT(*) FROM games WHERE ip = ?", (ip,)
            ).fetchone()
            self._db.execute("COMMIT")
            return used
        except sqlite3.Error:
            self._db.execute("ROLLBACK")
            raise

    def allow(self, ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            if self._db is None:
                history = self._prune_mem(ip, cutoff)
                if len(history) >= self.max_games:
                    return False
                history.append(now)
                return True
            return self._db_write(ip, now, cutoff)

    def status(self, ip: str) -> dict:
        cutoff = time.time() - self.window_seconds
        with self._lock:
            if self._db is None:
                history = self._prune_mem(ip, cutoff)
                used = len(history)
            else:
                used = self._db_count(ip, cutoff)
        return {
            "limit": self.max_games,
            "window_seconds": self.window_seconds,
            "used": used,
            "remaining": max(self.max_games - used, 0),
        }
