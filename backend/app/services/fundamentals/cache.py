from __future__ import annotations

import threading
import time
from typing import Callable

from ...config import settings

_lock = threading.Lock()
_cache: dict[str, tuple[float, object]] = {}
_overrides: dict[str, object] = {}


def _ttl() -> float:
    return float(settings.fundamentals_cache_ttl_seconds)


def get_cached(symbol: str) -> object | None:
    override = _overrides.get(symbol)
    if override is not None:
        return override
    with _lock:
        entry = _cache.get(symbol)
    if entry is None:
        return None
    ts, value = entry
    if time.monotonic() - ts > _ttl():
        with _lock:
            _cache.pop(symbol, None)
        return None
    return value


def put_cached(symbol: str, value: object) -> None:
    if symbol in _overrides:
        return
    with _lock:
        _cache[symbol] = (time.monotonic(), value)


def set_override(symbol: str, value: object) -> None:
    _overrides[symbol] = value


def clear_overrides() -> None:
    _overrides.clear()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def with_cache(loader: Callable[[str], object], symbol: str) -> object:
    cached = get_cached(symbol)
    if cached is not None:
        return cached
    value = loader(symbol)
    put_cached(symbol, value)
    return value
