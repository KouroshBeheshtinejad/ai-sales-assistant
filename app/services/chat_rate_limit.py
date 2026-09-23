from collections import deque
from collections import OrderedDict
from dataclasses import dataclass
import os
from threading import Lock
import time

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class RateLimitSettings:
    max_requests: int
    window_seconds: float
    max_keys: int


def _positive_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def get_rate_limit_settings() -> RateLimitSettings:
    try:
        window_seconds = max(1.0, float(os.getenv("AI_CHAT_RATE_LIMIT_WINDOW_SECONDS", "60")))
    except ValueError:
        window_seconds = 60.0
    return RateLimitSettings(
        max_requests=_positive_int("AI_CHAT_RATE_LIMIT_REQUESTS", 20),
        window_seconds=window_seconds,
        max_keys=_positive_int("AI_CHAT_RATE_LIMIT_MAX_KEYS", 10000),
    )


class InMemoryChatRateLimiter:
    def __init__(self):
        self._events: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    def allow(self, key: str, settings: RateLimitSettings, now: float | None = None) -> bool:
        current_time = time.monotonic() if now is None else now
        cutoff = current_time - settings.window_seconds
        with self._lock:
            events = self._events.setdefault(key, deque())
            self._events.move_to_end(key)
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= settings.max_requests:
                return False
            events.append(current_time)
            if len(self._events) > settings.max_keys:
                self._events.popitem(last=False)
            return True

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


limiter = InMemoryChatRateLimiter()
auth_limiter = InMemoryChatRateLimiter()
tracking_limiter = InMemoryChatRateLimiter()


def enforce_chat_rate_limit(request: Request) -> None:
    # The direct socket peer is used; forwarded headers are not trusted here.
    client_host = request.client.host if request.client else "unknown"
    store_id = request.path_params.get("store_id", "unknown")
    key = f"{client_host}:{store_id}"
    settings = get_rate_limit_settings()
    if not limiter.allow(key, settings):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many chat requests. Please try again later.",
            headers={"Retry-After": str(int(settings.window_seconds))},
        )


def enforce_auth_rate_limit(request: Request, action: str) -> None:
    client_host = request.client.host if request.client else "unknown"
    try:
        max_requests = max(1, int(os.getenv("AUTH_RATE_LIMIT_REQUESTS", "10")))
    except ValueError:
        max_requests = 10
    try:
        window_seconds = max(1.0, float(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")))
    except ValueError:
        window_seconds = 60.0
    settings = RateLimitSettings(max_requests=max_requests, window_seconds=window_seconds, max_keys=10000)
    if not auth_limiter.allow(f"{action}:{client_host}", settings):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": str(int(window_seconds))},
        )


def enforce_tracking_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    try:
        max_requests = max(1, int(os.getenv("TRACKING_RATE_LIMIT_REQUESTS", "30")))
    except ValueError:
        max_requests = 30
    try:
        window_seconds = max(1.0, float(os.getenv("TRACKING_RATE_LIMIT_WINDOW_SECONDS", "60")))
    except ValueError:
        window_seconds = 60.0
    settings = RateLimitSettings(
        max_requests=max_requests,
        window_seconds=window_seconds,
        max_keys=10000,
    )
    if not tracking_limiter.allow(client_host, settings):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many tracking requests. Please try again later.",
            headers={"Retry-After": str(int(window_seconds))},
        )
