from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, status

from ..config import settings


class ExternalAPIRateLimiter:
    def __init__(self):
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, identity: str) -> None:
        now = monotonic()
        window_start = now - 60
        with self._lock:
            requests = self._requests[identity]
            while requests and requests[0] <= window_start:
                requests.popleft()
            if len(requests) >= settings.external_api_rate_limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Try again later.",
                    headers={"Retry-After": "60"},
                )
            requests.append(now)


_limiter = ExternalAPIRateLimiter()


def get_external_api_rate_limiter() -> ExternalAPIRateLimiter:
    return _limiter
