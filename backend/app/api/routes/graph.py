"""Graph diagnostics endpoints."""

from __future__ import annotations

import threading
import time

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_graph_store
from app.db.falkor import GraphStore
from app.schemas.health import GraphPingResponse, GraphStatsResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/ping", response_model=GraphPingResponse)
def graph_ping(store: GraphStore = Depends(get_graph_store)) -> GraphPingResponse:
    """Round-trip latency to FalkorDB and list of graphs. 503 if unreachable."""
    return GraphPingResponse(**store.ping())


@router.get("/stats", response_model=GraphStatsResponse)
def graph_stats(request: Request, store: GraphStore = Depends(get_graph_store)) -> GraphStatsResponse:
    """Node/edge counts cached briefly to avoid repeated full graph scans."""
    lock = getattr(request.app.state, "stats_lock", None)
    if lock is None:
        lock = threading.Lock()
        request.app.state.stats_lock = lock

    with lock:
        cached = getattr(request.app.state, "stats_cache", None)
        if cached and time.monotonic() - cached[0] < 5:
            return cached[1]

        # Total node count
        node_result = store.ro_query("MATCH (n) RETURN count(n)").result_set
        node_count = node_result[0][0] if node_result else 0

        # Total edge count
        edge_result = store.ro_query("MATCH ()-[r]->() RETURN count(r)").result_set
        edge_count = edge_result[0][0] if edge_result else 0

        # Per-label counts
        label_result = store.ro_query(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC"
        ).result_set
        labels = {row[0]: row[1] for row in label_result} if label_result else {}

        response = GraphStatsResponse(
            node_count=node_count,
            edge_count=edge_count,
            labels=labels,
        )
        request.app.state.stats_cache = (time.monotonic(), response)
        return response
