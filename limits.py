import threading
import time
from collections import deque


class GameLimiter:
    def __init__(self, max_games: int = 10, window_seconds: int = 24 * 3600):
        self.max_games = max_games
        self.window_seconds = window_seconds
        self._games: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, ip: str) -> bool:
        now = time.time()
        with self._lock:
            history = self._games.setdefault(ip, deque())
            cutoff = now - self.window_seconds
            while history and history[0] < cutoff:
                history.popleft()
            if len(history) >= self.max_games:
                return False
            history.append(now)
            return True
