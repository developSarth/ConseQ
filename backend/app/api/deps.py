"""FastAPI dependency providers (injected into route handlers)."""

from __future__ import annotations

from fastapi import Request

from app.core.config import Settings, get_settings
from app.db.falkor import GraphStore
from app.services.fork import ForkManager


def get_graph_store(request: Request) -> GraphStore:
    """Return the process-wide GraphStore created in the app lifespan."""
    return request.app.state.graph_store


def get_fork_manager(request: Request) -> ForkManager:
    """Return the process-wide ForkManager created in the app lifespan."""
    return request.app.state.fork_manager


def settings_dep() -> Settings:
    """Expose cached settings as a dependency (overridable in tests)."""
    return get_settings()
