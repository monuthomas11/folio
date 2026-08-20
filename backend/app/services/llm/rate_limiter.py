from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable

from ...config import settings

WINDOW_SECONDS = 60.0


class LLMRateLimiter:
    def __init__(
        self,
        max_requests_per_minute: int,
        min_request_interval_seconds: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        if max_requests_per_minute <= 0:
            raise ValueError("max_requests_per_minute must be greater than zero")
        if min_request_interval_seconds < 0:
            raise ValueError("min_request_interval_seconds cannot be negative")

        self.max_requests_per_minute = max_requests_per_minute
        self.min_request_interval_seconds = max(
            min_request_interval_seconds,
            WINDOW_SECONDS / max_requests_per_minute,
        )
        self._clock = clock
        self._sleep = sleep
        self._request_times: deque[float] = deque()
        self._last_request_at: float | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = self._clock()
                window_start = now - WINDOW_SECONDS
                while (
                    self._request_times
                    and self._request_times[0] <= window_start
                ):
                    self._request_times.popleft()

                wait_seconds = 0.0
                if len(self._request_times) >= self.max_requests_per_minute:
                    wait_seconds = max(
                        wait_seconds,
                        self._request_times[0] + WINDOW_SECONDS - now,
                    )
                if self._last_request_at is not None:
                    wait_seconds = max(
                        wait_seconds,
                        self._last_request_at
                        + self.min_request_interval_seconds
                        - now,
                    )

                if wait_seconds <= 0:
                    self._request_times.append(now)
                    self._last_request_at = now
                    return

                await self._sleep(wait_seconds)


_limiters: dict[tuple[int, float], LLMRateLimiter] = {}


def get_llm_rate_limiter() -> LLMRateLimiter:
    key = (
        int(settings.llm_max_requests_per_minute),
        float(settings.llm_min_request_interval_seconds),
    )
    limiter = _limiters.get(key)
    if limiter is None:
        limiter = LLMRateLimiter(*key)
        _limiters[key] = limiter
    return limiter
