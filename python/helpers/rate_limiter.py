import asyncio
import time
from collections import deque
from typing import Callable, Awaitable


class RateLimiter:
    def __init__(self, seconds: int = 60, **limits: int):
        self.timeframe = seconds
        self.limits = {k: v if isinstance(v, (int, float)) else 0 for k, v in (limits or {}).items()}
        self.values: dict[str, deque] = {k: deque() for k in self.limits}
        self._lock = asyncio.Lock()

    def add(self, **kwargs: int):
        now = time.time()
        for key, value in kwargs.items():
            if key not in self.values:
                self.values[key] = deque()
            self.values[key].append((now, value))

    async def cleanup(self):
        async with self._lock:
            cutoff = time.time() - self.timeframe
            for key in self.values:
                d = self.values[key]
                while d and d[0][0] <= cutoff:
                    d.popleft()

    async def get_total(self, key: str) -> int:
        async with self._lock:
            return sum(v for _, v in self.values.get(key, []))

    async def wait(self, callback: Callable[[str, str, int, int], Awaitable[bool]] | None = None):
        while True:
            await self.cleanup()
            should_wait = False
            for key, limit in self.limits.items():
                if limit <= 0:
                    continue
                total = await self.get_total(key)
                if total > limit:
                    if callback:
                        msg = f"Rate limit exceeded for {key} ({total}/{limit}), waiting..."
                        should_wait = not await callback(msg, key, total, limit)
                    else:
                        should_wait = True
                    break
            if not should_wait:
                break
            await asyncio.sleep(1)
