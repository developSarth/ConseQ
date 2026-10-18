"""Response models for health and graph diagnostics endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    version: str
    environment: str
    uptime_s: float


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded"]
    falkordb: bool
    schema_ready: bool
    gemini_key_configured: bool
    schema_version: int | None


class GraphPingResponse(BaseModel):
    host: str
    latency_ms: float
    graph: str
    graph_exists: bool
    graphs: list[str]


class GraphStatsResponse(BaseModel):
    node_count: int
    edge_count: int
    labels: dict[str, int]
