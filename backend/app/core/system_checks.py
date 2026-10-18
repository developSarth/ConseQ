"""Environment checks used by the readiness probe.

ConseQ does not need FFmpeg or local storage — it is a pure graph + LLM project.
This module now only checks FalkorDB connectivity (handled via GraphStore.is_healthy)
and Gemini key presence. Kept as a module for future extensibility.
"""

from __future__ import annotations


def check_gemini_configured(key_present: bool) -> str:
    """Return a human-readable status for the Gemini API key."""
    return "configured" if key_present else "missing"
