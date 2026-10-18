"""FastAPI application entrypoint for ECHO.

Run from the `backend/` directory:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import graph, health, project, simulate
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, register_exception_handlers
from app.db.falkor import GraphStore
from app.db.schema import ensure_schema
from app.services.fork import ForkManager

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: logging, FalkorDB connection, schema bootstrap. Shutdown: cleanup."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app.state.started_at = time.monotonic()
    app.state.stats_lock = threading.Lock()
    app.state.stats_cache = None
    store = GraphStore(settings)
    connected = store.connect()
    app.state.graph_store = store

    # Bootstrap the software architecture schema (indexes + constraints)
    if connected:
        try:
            ensure_schema(store)
        except Exception:
            log.exception("Schema bootstrap failed; readiness will remain degraded")

    # Fork manager for simulations
    fork_mgr = ForkManager(store, settings)
    app.state.fork_manager = fork_mgr
    if connected:
        try:
            fork_mgr.cleanup_orphaned_forks()
        except Exception:
            log.exception("Orphaned fork cleanup failed during startup")

    log.info("ECHO startup complete (env=%s, version=%s, db=%s)",
             settings.environment, __version__, "connected" if connected else "degraded")
    try:
        yield
    finally:
        # Destroy any lingering forks on shutdown
        fm: ForkManager = app.state.fork_manager
        destroyed = fm.destroy_all()
        if destroyed:
            log.info("Cleaned up %d simulation fork(s) on shutdown", destroyed)
        store.close()
        log.info("Shutdown complete")


def create_app() -> FastAPI:
    """App factory — used by uvicorn and by tests."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "ECHO — AI-Powered Software Failure Simulator. "
            "Simulates cascading consequences of service outages, dependency upgrades, "
            "and failovers using temporary FalkorDB graph forks."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID", "Accept"],
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
    )
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(graph.router)
    app.include_router(simulate.router)
    app.include_router(project.router)
    return app


app = create_app()
