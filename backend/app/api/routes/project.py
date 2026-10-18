"""API routes for codebase repository ingestion (.zip or local directory) and project graph management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.agent.tools import get_topology_graph
from app.api.deps import get_graph_store
from app.db.falkor import GraphStore
from app.schemas.project import IngestDirectoryRequest, IngestResponse
from app.schemas.simulation import TopologyResponse
from app.services.ingest import IngestionError, SecurityValidationError, ingest_local_directory, ingest_zip_archive

log = logging.getLogger("app.api.routes.project")

router = APIRouter(prefix="/project", tags=["Project Ingestion"])


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_ingest_zip(
    file: UploadFile = File(..., description="ZIP archive of the codebase or microservice repository"),
    project_name: str | None = Form(default=None, description="Optional custom project name"),
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
        content = await file.read()
        return ingest_zip_archive(
            zip_bytes=content,
            filename=file.filename,
            store=store,
            project_name=project_name,
        )
    except SecurityValidationError as exc:
        log.warning("Security validation failed during zip ingestion: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IngestionError as exc:
        log.warning("Ingestion failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Unexpected error during zip ingestion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the repository archive: {exc}",
        ) from exc


@router.post("/ingest-directory", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
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
    except Exception as exc:
        log.exception("Unexpected error during directory ingestion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while inspecting the directory: {exc}",
        ) from exc


@router.get("/{project_id}/topology", response_model=TopologyResponse)
def get_project_topology(
    project_id: str,
    store: GraphStore = Depends(get_graph_store),
) -> TopologyResponse:
    """Returns the visual node/edge topology for an ingested project graph."""
    try:
        return get_topology_graph(store, graph=project_id, node_limit=1000, edge_limit=2500)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project graph '{project_id}' not found or unreachable: {exc}",
        ) from exc


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project_graph(
    project_id: str,
    store: GraphStore = Depends(get_graph_store),
) -> dict[str, Any]:
    """Cleans up and deletes a dedicated project graph from FalkorDB."""
    if not project_id.startswith("proj_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete non-project graphs.",
        )
    try:
        store.graph(project_id).delete()
        return {"status": "deleted", "project_id": project_id}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project graph '{project_id}': {exc}",
        ) from exc
