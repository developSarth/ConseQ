"""API routes for codebase repository ingestion (.zip or local directory) and project graph management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.agent.tools import get_topology_graph
from app.api.deps import get_graph_store, settings_dep
from app.core.config import Settings
from app.core.middleware import GraphUnavailableError
from app.core.rate_limiter import rate_limit_project_ingest
from app.db.falkor import GraphStore
from app.schemas.project import IngestDirectoryRequest, IngestResponse
from app.schemas.simulation import TopologyResponse
from app.services.ingest import (
    MAX_ARCHIVE_SIZE_BYTES,
    IngestionError,
    SecurityValidationError,
    ingest_local_directory,
    ingest_zip_archive,
)
from app.services.project_ids import is_project_graph_id

log = logging.getLogger("app.api.routes.project")

router = APIRouter(prefix="/project", tags=["Project Ingestion"])


def _require_existing_project(project_id: str, store: GraphStore, settings: Settings) -> None:
    if not is_project_graph_id(project_id) or project_id == settings.falkordb_graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    if project_id not in store.db.list_graphs():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")


@router.post(
    "/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_project_ingest)],
)
async def upload_and_ingest_zip(
    file: UploadFile = File(..., description="ZIP archive of the codebase or microservice repository"),
    project_name: str | None = Form(default=None, max_length=128, description="Optional custom project name"),
    store: GraphStore = Depends(get_graph_store),
) -> IngestResponse:
    """Ingest a zipped codebase archive, extracts services, endpoints, databases, and dependencies,

    and populates a dedicated FalkorDB project graph for what-if failure simulations.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip archive files are accepted for codebase ingestion.",
        )

    try:
        content = await file.read(MAX_ARCHIVE_SIZE_BYTES + 1)
        return await run_in_threadpool(
            ingest_zip_archive,
            content,
            file.filename,
            store,
            project_name,
        )
    except SecurityValidationError as exc:
        log.warning("Security validation failed during zip ingestion: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IngestionError as exc:
        log.warning("Ingestion failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except GraphUnavailableError:
        raise
    except Exception as exc:
        log.exception("Unexpected error during zip ingestion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the repository archive.",
        ) from exc
    finally:
        await file.close()


@router.post(
    "/ingest-directory", response_model=IngestResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_project_ingest)],
)
def ingest_directory(
    request: IngestDirectoryRequest,
    store: GraphStore = Depends(get_graph_store),
) -> IngestResponse:
    """Ingest and analyze a local repository directory on the host server."""
    try:
        return ingest_local_directory(
            directory_path=request.directory_path,
            store=store,
            project_name=request.project_name,
        )
    except IngestionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except GraphUnavailableError:
        raise
    except Exception as exc:
        log.exception("Unexpected error during directory ingestion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while inspecting the directory.",
        ) from exc


@router.get("/{project_id}/topology", response_model=TopologyResponse)
def get_project_topology(
    project_id: str,
    store: GraphStore = Depends(get_graph_store),
    settings: Settings = Depends(settings_dep),
) -> TopologyResponse:
    """Returns the visual node/edge topology for an ingested project graph."""
    _require_existing_project(project_id, store, settings)
    return get_topology_graph(store, graph=project_id, node_limit=1000, edge_limit=2500)


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project_graph(
    project_id: str,
    store: GraphStore = Depends(get_graph_store),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Cleans up and deletes a dedicated project graph from FalkorDB."""
    _require_existing_project(project_id, store, settings)
    try:
        store.graph(project_id).delete()
        return {"status": "deleted", "project_id": project_id}
    except GraphUnavailableError:
        raise
    except Exception as exc:
        log.exception("Failed to delete project graph '%s'", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project graph.",
        ) from exc
