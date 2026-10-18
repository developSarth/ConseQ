"""API routes for ECHO software failure simulations and topology discovery."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.agent.runner import run_simulation
from app.agent.tools import get_topology_graph
from app.api.deps import get_fork_manager, get_graph_store, settings_dep
from app.core.config import Settings
from app.db.falkor import GraphStore
from app.core.rate_limiter import rate_limit_simulation
from app.schemas.simulation import (
    SimulationReport,
    SimulationRequest,
    TopologyResponse,
)
from app.services.fork import ForkManager

log = logging.getLogger("app.api.routes.simulate")

router = APIRouter(prefix="", tags=["Simulation"])


@router.post("/simulate", response_model=SimulationReport, dependencies=[Depends(rate_limit_simulation)])
def simulate_scenario(
    request: SimulationRequest,
    store: GraphStore = Depends(get_graph_store),
    fork_mgr: ForkManager = Depends(get_fork_manager),
    settings: Settings = Depends(settings_dep),
) -> SimulationReport:
    """Run an AI-powered what-if software simulation.

    Accepts natural language scenarios such as:
    - "What happens if our authentication service goes offline?"
    - "What if I upgrade this shared library to version 3?"
    - "How can we keep checkout working if the payment provider fails?"
    """
    log.info("Simulating scenario: '%s'", request.prompt[:120])
    return run_simulation(request, store, fork_mgr, settings)


@router.get("/simulate/scenarios")
def get_preset_scenarios() -> list[dict[str, Any]]:
    """Returns curated demo scenarios for one-click testing in the UI."""
    return [
        {
            "id": "scenario_stripe_fallback",
            "title": "Flash Sale Stripe Gateway Timeout",
            "type": "recovery",
            "prompt": "How can we keep checkout working if the payment provider fails?",
            "target": "tp_stripe",
            "description": "Tests automated failover routes to PayPal backup when primary Stripe payment gateway times out during flash sales.",
            "badge": "Payment Failover",
        },
        {
            "id": "scenario_auth_outage",
            "title": "Customer Auth & Session Collapse",
            "type": "failure",
            "prompt": "What happens if our authentication service goes offline?",
            "target": "auth-service",
            "description": "Simulates complete loss of auth-service and traces multi-hop breakage locking out 105,000 active shopping carts.",
            "badge": "Funnel Outage",
        },
        {
            "id": "scenario_order_db_crash",
            "title": "Orders PostgreSQL DB Deadlock",
            "type": "failure",
            "prompt": "What happens if our orders PostgreSQL database crashes?",
            "target": "db_order_pg",
            "description": "Simulates datastore outage on mission-critical order-service and assesses async Kafka queue buffering.",
            "badge": "Data Store Crash",
        },
        {
            "id": "scenario_jwt_upgrade",
            "title": "Upgrade crypto-jwt to v3.0",
            "type": "upgrade",
            "prompt": "What if I upgrade crypto-jwt to version 3?",
            "target": "crypto-jwt",
            "target_version": "3.0.0",
            "description": "Assesses dependency ripple effects across auth and user identity before major token signature upgrade.",
            "badge": "SDK Upgrade",
        },
    ]


@router.get("/graph/topology", response_model=TopologyResponse)
def get_architecture_topology(
    affected_id: str | None = Query(default=None, description="Optional node ID to highlight as affected"),
    node_limit: int = Query(default=1000, ge=1, le=5000),
    edge_limit: int = Query(default=2500, ge=1, le=10000),
    store: GraphStore = Depends(get_graph_store),
) -> TopologyResponse:
    """Returns a bounded topology page for interactive graph visualization."""
    affected_set = {affected_id} if affected_id else set()
    return get_topology_graph(
        store, affected_ids=affected_set, node_limit=node_limit, edge_limit=edge_limit
    )
