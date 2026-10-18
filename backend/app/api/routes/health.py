"""Liveness and readiness probes for ConseQ."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request, Response

from app import __version__
from app.api.deps import get_graph_store, settings_dep
from app.core.config import Settings
from app.db.falkor import GraphStore
from app.db.schema import ensure_schema, schema_ready
from app.schemas.health import LivenessResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=LivenessResponse)
def liveness(request: Request, settings: Settings = Depends(settings_dep)) -> LivenessResponse:
    """Is the process alive? No dependencies touched — always fast, always 200."""
    return LivenessResponse(
        app=settings.app_name,
        version=__version__,
        environment=settings.environment,
        uptime_s=round(time.monotonic() - request.app.state.started_at, 2),
    )


@router.get("/ready", response_model=ReadinessResponse)
def readiness(
    request: Request,
    response: Response,
    settings: Settings = Depends(settings_dep),
    store: GraphStore = Depends(get_graph_store),
) -> ReadinessResponse:
    """Can the app do real work? Checks FalkorDB and Gemini key. 503 if not."""
    falkor_ok = store.is_healthy()
    gemini_ok = settings.gemini_api_key is not None

    # Check current schema state so externally removed indexes or constraints
    # make readiness fail; bootstrap if the database only just recovered.
    is_schema_ready = schema_ready(store) if falkor_ok else False
    if falkor_ok and not is_schema_ready:
        try:
            ensure_schema(store)
            is_schema_ready = schema_ready(store)
        except Exception:
            is_schema_ready = False

    schema_version: int | None = None
    if falkor_ok:
        try:
            result = store.ro_query(
                "MATCH (m:SchemaMeta {id:'schema'}) RETURN m.version"
            ).result_set
            if result:
                schema_version = result[0][0]
        except Exception:
            pass

    ready = falkor_ok and is_schema_ready
    if not ready:
        response.status_code = 503
    return ReadinessResponse(
        status="ready" if ready else "degraded",
        falkordb=falkor_ok,
        schema_ready=is_schema_ready,
        gemini_key_configured=gemini_ok,
        schema_version=schema_version,
    )
