"""Logging setup and request-scoped correlation IDs."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

# Holds the current request's ID; "-" outside of a request (startup, workers).
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIdFilter(logging.Filter):
    """Injects the current request ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once. Safe to call multiple times (idempotent)."""
    root = logging.getLogger()
    if getattr(root, "_graphhacks_configured", False):
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | req=%(request_id)s | %(message)s"
        )
    )
    root.handlers = [handler]
    root.setLevel(level)
    root._graphhacks_configured = True  # type: ignore[attr-defined]

    # Quiet noisy libraries.
    for noisy in ("uvicorn.access", "httpx", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
