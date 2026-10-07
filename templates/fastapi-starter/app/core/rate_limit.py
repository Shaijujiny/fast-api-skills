"""Rate limiting with a pluggable backend (blueprint ch. 8, fastapi-auth ch. 02).

- `MemoryBackend`: default for dev/test. Single process only: counters are not shared between workers.
- `RedisBackend`: used when REDIS_URL is set. `redis` is imported lazily, so it stays an optional dependency.

`rate_limit(key, limit, window)` is a route dependency keyed by `key` + client IP. When the key must include
something from the body (e.g. the email), call `enforce_rate_limit(...)` from the service instead.
Over the limit -> HTTPException(429, Retry-After), rendered by the global 429 handler in exceptions.py.
"""

import threading
import time
from collections.abc import Callable
from typing import Protocol

from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitBackend(Protocol):
    def hit(self, key: str, window: int) -> tuple[int, int]:
        """Count one hit in the current window. Return (hits_so_far, seconds_until_window_resets)."""

    def reset(self) -> None: ...


class MemoryBackend:
    def __init__(self) -> None:
        self._data: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, window: int) -> tuple[int, int]:
        now = time.monotonic()
        with self._lock:
            count, reset_at = self._data.get(key, (0, 0.0))
            if reset_at <= now:
                count, reset_at = 0, now + window
                if len(self._data) > 10_000:  # opportunistic cleanup of expired windows
                    self._data = {k: v for k, v in self._data.items() if v[1] > now}
            count += 1
            self._data[key] = (count, reset_at)
            return count, max(1, int(reset_at - now + 0.999))

    def reset(self) -> None:
        with self._lock:
            self._data.clear()


class RedisBackend:
    def __init__(self, url: str, client=None) -> None:
        if client is None:
            import redis  # lazy: optional dependency

            client = redis.Redis.from_url(url)
        self._r = client

    def hit(self, key: str, window: int) -> tuple[int, int]:
        k = f"rl:{key}"
        pipe = self._r.pipeline()
        pipe.incr(k)
        pipe.expire(k, window, nx=True)  # set the TTL only on the first hit of a window
        pipe.ttl(k)
        count, _, ttl = pipe.execute()
        return int(count), max(1, int(ttl) if ttl and ttl > 0 else window)

    def reset(self) -> None:  # tests / ops only
        for k in self._r.scan_iter("rl:*"):
            self._r.delete(k)


_backend: RateLimitBackend | None = None


def get_backend() -> RateLimitBackend:
    global _backend
    if _backend is None:
        url = get_settings().redis_url
        _backend = RedisBackend(url) if url else MemoryBackend()
    return _backend


def set_backend(backend: RateLimitBackend | None) -> None:
    """Swap the backend (tests, custom stores). None re-resolves from settings on next use."""
    global _backend
    _backend = backend


def client_ip(request: Request) -> str:
    # Behind a proxy run uvicorn with --proxy-headers and --forwarded-allow-ips so this is the real client.
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(key: str, limit: int, window: int) -> None:
    try:
        count, retry_after = get_backend().hit(key, window)
    except Exception:  # a broken limiter store must not take login down; the failure is logged loudly
        logger.exception("rate limit backend failed; allowing request")
        return
    if count > limit:
        raise HTTPException(429, "rate limited", headers={"Retry-After": str(retry_after)})


def rate_limit(key: str, limit: int | Callable[[], int], window: int | Callable[[], int]):
    """Dependency factory. `limit`/`window` may be callables so settings are read per request."""

    def dependency(request: Request) -> None:
        lim = limit() if callable(limit) else limit
        win = window() if callable(window) else window
        enforce_rate_limit(f"{key}:{client_ip(request)}", lim, win)

    return dependency
