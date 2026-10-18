"""Pydantic schemas for ECHO simulations, blast radius reports, and topology graphs."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class SimulationType(str, Enum):
    FAILURE = "failure"
    UPGRADE = "upgrade"
    RECOVERY = "recovery"


class SimulationRequest(BaseModel):
    """Natural language or structured simulation request."""
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language scenario or question",
        examples=["What happens if our authentication service goes offline?"],
    )
    simulation_type: SimulationType | None = Field(
        default=None,
        description="Explicit type override (if omitted, agent infers from prompt)",
    )
    target_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Optional explicit node ID target (e.g. 'svc_auth')",
    )
    target_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Target library version if requesting an upgrade (e.g. '3.0.0')",
    )
    graph: str | None = Field(
        default=None,
        max_length=128,
        description="Optional target graph or project ID to simulate against",
    )


class ServiceImpact(BaseModel):
    id: str
    name: str
    tier: int
    impact: Literal["outage", "degraded", "healthy"]
    hops_from_target: int
    team_name: str | None = None


class EndpointImpact(BaseModel):
    id: str
    path: str
    method: str
    status: Literal["broken", "degraded", "operational"]
    service_id: str


class ClientImpact(BaseModel):
    id: str
    name: str
    platform: str
    active_users: int
    affected_endpoints: list[str] = Field(default_factory=list)


class TeamAlert(BaseModel):
    id: str
    name: str
    slack_channel: str
    oncall_lead: str
    reason: str


class OutageSimulationResult(BaseModel):
    target_id: str
    target_name: str
    target_type: str
    blast_radius_percent: float = Field(..., ge=0.0, le=100.0)
    tier1_services_down: int
    tier2_services_down: int
    tier3_services_down: int = 0
    impacted_services: list[ServiceImpact] = Field(default_factory=list)
    broken_endpoints: list[EndpointImpact] = Field(default_factory=list)
    impacted_clients: list[ClientImpact] = Field(default_factory=list)
    impacted_teams: list[TeamAlert] = Field(default_factory=list)


class UpgradeImpactResult(BaseModel):
    library_id: str
    library_name: str
    current_version: str
    target_version: str
    is_major_breaking_bump: bool
    dependent_services: list[dict[str, Any]] = Field(default_factory=list)
    dependent_teams: list[TeamAlert] = Field(default_factory=list)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recommended_upgrade_order: list[str] = Field(default_factory=list)


class RecoveryPlanResult(BaseModel):
    failing_entity_id: str
    failing_entity_name: str
    primary_provider: str
    fallback_provider: str | None = None
    fallback_available: bool
    estimated_recovery_rate: float | None = Field(
        default=None,
        description="Not measured by this assessment; null until failover is simulated and observed.",
    )
    mitigation_steps: list[str] = Field(default_factory=list)
    degraded_mode_strategy: str


class SimulationReport(BaseModel):
    """The complete executive simulation artifact returned by the agent."""
    id: str
    prompt: str
    type: SimulationType
    target_entity: str
    executive_summary: str
    blast_radius_score: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Measured service blast radius for failure runs; zero for assessment-only run types.",
    )
    outage_details: OutageSimulationResult | None = None
    upgrade_details: UpgradeImpactResult | None = None
    recovery_details: RecoveryPlanResult | None = None
    actionable_recommendations: list[str] = Field(default_factory=list)
    fork_graph: str = Field(description="Fork identifier for failure runs; not_created for assessment-only runs.")
    execution_time_ms: float
    created_at: float


# ── Topology Schema for Visualizer ──────────────────────────────────────────

class TopologyNode(BaseModel):
    id: str
    name: str
    label: str  # Service, APIEndpoint, Database, ThirdParty, Library, ClientApp
    tier: int | None = None
    status: str = "healthy"
    category: str | None = None
    platform: str | None = None
    is_affected: bool = False


class TopologyLink(BaseModel):
    source: str
    target: str
    type: str  # CALLS, CONNECTS_TO, INTEGRATES_WITH, USES_LIBRARY, FALLBACK_FOR, ROUTED_TO
    is_broken: bool = False


class TopologyResponse(BaseModel):
    nodes: list[TopologyNode]
    links: list[TopologyLink]
    total_nodes: int
    total_links: int
    truncated: bool = False
