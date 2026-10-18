"""Pydantic schemas for codebase directory & zip archive ingestion."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Result of analyzing and loading a codebase into FalkorDB."""
    project_id: str = Field(description="Unique FalkorDB graph identifier for this project")
    project_name: str = Field(description="Human-readable project or repository name")
    node_count: int = Field(default=0, description="Total nodes created in project graph")
    edge_count: int = Field(default=0, description="Total dependency edges created")
    services_count: int = Field(default=0)
    databases_count: int = Field(default=0)
    endpoints_count: int = Field(default=0)
    third_parties_count: int = Field(default=0)
    libraries_count: int = Field(default=0)
    services: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    endpoints: list[str] = Field(default_factory=list)
    libraries: list[str] = Field(default_factory=list)
    execution_time_ms: float = Field(default=0.0)
    message: str = Field(default="Codebase successfully ingested and analyzed.")


class IngestDirectoryRequest(BaseModel):
    """Request to analyze a local directory on the server/host."""
    directory_path: str = Field(..., min_length=1, max_length=1024, description="Absolute or relative path to project directory")
    project_name: str | None = Field(default=None, max_length=128, description="Optional custom name for project")
