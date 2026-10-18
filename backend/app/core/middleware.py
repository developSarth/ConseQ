"""HTTP middleware and global exception handlers."""

from __future__ import annotations

import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_ctx

log = logging.getLogger("app.http")

_VALID_RID = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


class RequestContextMiddleware:
    """Pure ASGI middleware: assigns a validated request ID, times the request, logs."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract and validate X-Request-ID from ASGI headers
        rid = ""
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                rid = value.decode("latin-1", errors="replace")
                break
        if not rid or not _VALID_RID.match(rid):
            rid = uuid.uuid4().hex[:12]

        token = request_id_ctx.set(rid)
        start = time.perf_counter()

        async def send_with_tracking(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter() - start) * 1000
                extra = [
                    (b"x-request-id", rid.encode("latin-1")),
                    (b"x-response-time-ms", f"{elapsed_ms:.1f}".encode("latin-1")),
                ]
                headers = list(message.get("headers", [])) + extra
                message = {**message, "headers": headers}
                log.info(
                    "%s %s -> %s (%.1f ms) req=%s",
                    scope.get("method", "?"),
                    scope.get("path", "/"),
                    message.get("status", 0),
                    elapsed_ms,
                    rid,
                )
            await send(message)

        try:
            await self.app(scope, receive, send_with_tracking)
        finally:
            request_id_ctx.reset(token)


class GraphUnavailableError(RuntimeError):
    """Raised when FalkorDB cannot be reached; mapped to HTTP 503."""


class TargetNotFoundError(LookupError):
    """Raised when a requested architecture entity does not exist."""


class InvalidSimulationTargetError(ValueError):
    """Raised when an existing entity does not support the requested simulation."""


class RateLimitExceededError(RuntimeError):
    """Raised when client exceeds rate limits; mapped to HTTP 429."""


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain errors to consistent JSON responses (never leak stack traces)."""

    @app.exception_handler(GraphUnavailableError)
    async def _graph_unavailable(request: Request, exc: GraphUnavailableError):
        return JSONResponse(
            status_code=503,
            content={"error": "graph_unavailable", "detail": str(exc),
                     "request_id": request_id_ctx.get()},
        )

    @app.exception_handler(TargetNotFoundError)
    async def _target_not_found(request: Request, exc: TargetNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error": "target_not_found", "detail": str(exc),
                     "request_id": request_id_ctx.get()},
        )

    @app.exception_handler(InvalidSimulationTargetError)
    async def _invalid_simulation_target(request: Request, exc: InvalidSimulationTargetError):
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_simulation_target", "detail": str(exc),
                     "request_id": request_id_ctx.get()},
        )

    @app.exception_handler(RateLimitExceededError)
    async def _rate_limit_exceeded(request: Request, exc: RateLimitExceededError):
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded", "detail": str(exc),
                     "request_id": request_id_ctx.get()},
            headers={"Retry-After": "10"},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": "Unexpected server error.",
                     "request_id": request_id_ctx.get()},
        )
