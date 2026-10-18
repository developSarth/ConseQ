"""Gemini client singleton manager."""

from __future__ import annotations

import logging
import threading
from typing import Any

log = logging.getLogger("app.agent.client")

_client_lock = threading.Lock()
_cached_client: Any = None
_cached_key: str | None = None


def get_genai_client(api_key: str) -> Any:
    """Return a thread-safe cached genai.Client instance for the provided API key."""
    global _cached_client, _cached_key
    with _client_lock:
        if _cached_client is not None and _cached_key == api_key:
            return _cached_client
        try:
            from google import genai

            _cached_client = genai.Client(api_key=api_key)
            _cached_key = api_key
            log.debug("Initialized cached Gemini client")
            return _cached_client
        except Exception as exc:
            log.error("Failed to initialize genai.Client: %s", exc)
            raise
