"""In-memory rate limiter for resource-intensive endpoints."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict

from fastapi import Request

from app.core.middleware import RateLimitExceededError

log = logging.getLogger("app.rate_limiter")


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter per client IP."""

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            # Filter timestamps to within the active window
            history = [t for t in self._requests[client_ip] if t > cutoff]
            if len(history) >= self.max_requests:
                log.warning(
                    "Rate limit exceeded for client %s (%d requests in %.0fs)",
                    client_ip,
                    len(history),
                    self.window_seconds,
                )
                raise RateLimitExceededError(
                    f"Rate limit exceeded: maximum {self.max_requests} simulations per {int(self.window_seconds)} seconds."
                )
            history.append(now)
            self._requests[client_ip] = history


simulation_rate_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60.0)
project_ingest_rate_limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60.0)


def rate_limit_simulation(request: Request) -> None:
    """FastAPI dependency to rate limit /simulate calls."""
    simulation_rate_limiter.check(request)


def rate_limit_project_ingest(request: Request) -> None:
    """Keep archive parsing and graph writes from being flooded per client IP."""
    project_ingest_rate_limiter.check(request)
