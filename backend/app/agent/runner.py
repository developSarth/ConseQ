"""Simulation runner for ECHO — AI-Powered Software Failure Simulator.

Orchestrates:
1. Intent resolution from natural language
2. Isolated temporary graph fork creation in FalkorDB (g.copy)
3. Failure injection and analysis on the fork; graph-based upgrade and recovery assessments
4. Cypher cascade & blast radius metric calculation
5. Grounded executive report composition with Gemini Flash + evidence fallback
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any

from app.agent.parser import parse_intent
from app.agent.tools import (
    find_recovery_paths,
    resolve_target_entity,
    trace_library_upgrade_impact,
    trace_outage_blast_radius,
)
from app.core.config import Settings
from app.core.middleware import InvalidSimulationTargetError, TargetNotFoundError
from app.db.falkor import GraphStore
from app.schemas.simulation import (
    OutageSimulationResult,
    RecoveryPlanResult,
    SimulationReport,
    SimulationRequest,
    SimulationType,
    UpgradeImpactResult,
)
from app.services.fork import ForkManager
from app.services.project_ids import is_project_graph_id

log = logging.getLogger("app.agent.runner")


def _compose_summary_with_gemini(
    report_type: str,
    target_name: str,
    metrics: dict[str, Any],
    settings: Settings,
) -> str | None:
    """Invokes Gemini Flash to generate an executive briefing citing exact graph metrics."""
    api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None
    if not api_key:
        return None

    prompt = f"""You are the ECHO AI Software Reliability Engineer.
Write a concise, professional executive briefing (2-3 paragraphs) for engineering leadership
summarizing the {report_type} on '{target_name}'.

Strict ground rules:
- Cite ONLY the exact numbers, services, and impact metrics provided below.
- Do NOT hallucinate unlisted services or fictional metrics.
- Format with markdown bolding on critical numbers.

Simulation Evidence:
{metrics}
"""
    try:
        from app.agent.client import get_genai_client

        client = get_genai_client(api_key)
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        if resp and resp.text:
            return resp.text.strip()
    except Exception as exc:
        log.warning("Gemini summary synthesis failed (%s), using fallback template", exc)

    return None


_VALID_TARGET_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{1,128}$")


def run_simulation(
    request: SimulationRequest,
    store: GraphStore,
    fork_mgr: ForkManager,
    settings: Settings,
) -> SimulationReport:
    """Runs a complete end-to-end what-if simulation against FalkorDB."""
    start_time = time.monotonic()
    report_id = f"echo_{uuid.uuid4().hex[:10]}"

    # 1. Parse user intent (Gemini Flash or rule fallback)
    source_graph = request.graph or settings.falkordb_graph
    if source_graph != settings.falkordb_graph:
        if not is_project_graph_id(source_graph):
            raise InvalidSimulationTargetError("Only registered-format project graph IDs may be selected.")
        if source_graph not in store.db.list_graphs():
            raise TargetNotFoundError("The selected project graph no longer exists.")
    intent = parse_intent(request.prompt, settings)
    sim_type = request.simulation_type or intent.simulation_type
    target_name = request.target_id or intent.target_name
    target_version = request.target_version or intent.target_version or "3.0.0"

    if not _VALID_TARGET_RE.match(target_name):
        raise InvalidSimulationTargetError(f"Target identifier contains invalid characters: '{target_name}'")

    # 2. Resolve target entity in graph
    target_node = resolve_target_entity(
        store, target_name, graph=source_graph, exact_only=request.target_id is not None
    )
    if target_node is None:
        raise TargetNotFoundError(f"No architecture entity matched '{target_name}' in '{source_graph}'.")
    target_id = target_node["id"]
    resolved_name = target_node["name"]
    if sim_type == SimulationType.UPGRADE and target_node["label"] != "Library":
        raise InvalidSimulationTargetError(f"'{resolved_name}' is not a library and cannot be upgraded.")
    if sim_type == SimulationType.FAILURE and target_node["label"] not in (
        "Service", "Database", "ThirdParty"
    ):
        raise InvalidSimulationTargetError(
            f"Failure simulation is not supported for {target_node['label']} entities."
        )
    if sim_type == SimulationType.RECOVERY and target_node["label"] not in (
        "Service", "ThirdParty"
    ):
        raise InvalidSimulationTargetError(
            f"Recovery assessment is not supported for {target_node['label']} entities."
        )

    fork_id = "not_created"
    outage_details: OutageSimulationResult | None = None
    upgrade_details: UpgradeImpactResult | None = None
    recovery_details: RecoveryPlanResult | None = None
    recommendations: list[str] = []
    summary: str = ""
    blast_radius = 0.0

    # 3. Execute scenario based on type
    if sim_type == SimulationType.FAILURE:
        # Fail closed: simulations must never fall back to reading the live graph.
        fork_id = fork_mgr.create_fork(
            description=f"Outage simulation of {resolved_name}",
            source_graph=source_graph,
        )
        try:
            fork_mgr.apply_mutation(
                fork_id,
                "MATCH (n {id: $id}) SET n.status = 'offline'",
                {"id": target_id},
            )
            outage_details = trace_outage_blast_radius(store, target_id, graph=fork_id)
        finally:
            fork_mgr.destroy_fork(fork_id)
        blast_radius = outage_details.blast_radius_percent

        # Recommendations
        recommendations = [
            f"Alert {len(outage_details.impacted_teams)} on-call engineering teams immediately via PagerDuty/Slack.",
            f"Review circuit-breaker coverage across {len(outage_details.impacted_services)} affected services in the dependency chain.",
            f"Protect {sum(c.active_users for c in outage_details.impacted_clients):,} customer sessions with graceful degradation banners.",
        ]

        # Executive summary
        gemini_summary = _compose_summary_with_gemini(
            "outage failure simulation",
            resolved_name,
            {
                "target": resolved_name,
                "blast_radius_percent": blast_radius,
                "tier1_services_down": outage_details.tier1_services_down,
                "tier2_services_down": outage_details.tier2_services_down,
                "tier3_services_down": outage_details.tier3_services_down,
                "impacted_services_count": len(outage_details.impacted_services),
                "broken_endpoints_count": len(outage_details.broken_endpoints),
                "impacted_users": sum(c.active_users for c in outage_details.impacted_clients),
            },
            settings,
        )

        if gemini_summary:
            summary = gemini_summary
        else:
            total_users = sum(c.active_users for c in outage_details.impacted_clients)
            summary = (
                f"### Outage Blast Radius: **{blast_radius}% System Degradation**\n\n"
                f"Simulating an outage of **{resolved_name}** (`{target_id}`) affects **{len(outage_details.impacted_services)} dependent services**, "
                f"breaking **{len(outage_details.broken_endpoints)} customer-facing API endpoints** and putting **{total_users:,} active users** at risk. "
                f"**{outage_details.tier1_services_down} Tier 1 mission-critical services** are severely impaired."
            )

    elif sim_type == SimulationType.UPGRADE:
        upgrade_details = trace_library_upgrade_impact(
            store, library_name=resolved_name, target_version=target_version, graph=source_graph
        )
        # This is an impact estimate, not a simulated outage percentage.
        blast_radius = 0.0

        recommendations = [
            f"Deploy upgrade to {len(upgrade_details.dependent_services)} services in phased batches: {', '.join(upgrade_details.recommended_upgrade_order)}.",
            f"Run integration regression suites with {len(upgrade_details.dependent_teams)} owning engineering teams.",
            "Verify backward compatibility of serialized tokens and API request schemas before merging.",
        ]

        gemini_summary = _compose_summary_with_gemini(
            "library upgrade impact assessment",
            resolved_name,
            {
                "library": resolved_name,
                "current_version": upgrade_details.current_version,
                "target_version": target_version,
                "risk_level": upgrade_details.risk_level,
                "is_major_breaking_bump": upgrade_details.is_major_breaking_bump,
                "dependent_services_count": len(upgrade_details.dependent_services),
            },
            settings,
        )

        if gemini_summary:
            summary = gemini_summary
        else:
            summary = (
                f"### Upgrade Impact Assessment: **{upgrade_details.risk_level} Risk Level**\n\n"
                f"Upgrading **{upgrade_details.library_name}** from version `{upgrade_details.current_version}` to `{target_version}` "
                f"directly impacts **{len(upgrade_details.dependent_services)} microservices** across **{len(upgrade_details.dependent_teams)} teams**. "
                f"{'**Major breaking changes detected.**' if upgrade_details.is_major_breaking_bump else 'Minor/patch update with low regression risk.'}"
            )

    elif sim_type == SimulationType.RECOVERY:
        recovery_details = find_recovery_paths(store, target_id, graph=source_graph)
        # Recovery is a graph-based fallback assessment, not a forked failover.
        blast_radius = 0.0

        recommendations = recovery_details.mitigation_steps

        gemini_summary = _compose_summary_with_gemini(
            "fallback configuration assessment",
            resolved_name,
            {
                "failing_entity": resolved_name,
                "fallback_available": recovery_details.fallback_available,
                "fallback_provider": recovery_details.fallback_provider,
                "estimated_recovery_rate": None,
                "degraded_mode_strategy": recovery_details.degraded_mode_strategy,
            },
            settings,
        )

        if gemini_summary:
            summary = gemini_summary
        else:
            if recovery_details.fallback_available:
                summary = (
                    f"### Recovery Assessment: **Fallback configured**\n\n"
                    f"The graph links **{resolved_name}** to standby provider **{recovery_details.fallback_provider}**. "
                    "This is a configuration assessment; traffic restoration has not been measured by executing failover."
                )
            else:
                summary = (
                    f"### Recovery Assessment: **No registered fallback**\n\n"
                    f"The graph contains no registered standby for **{resolved_name}**. The listed degraded-mode steps are recommendations and have not been tested on a simulation fork."
                )

    duration_ms = round((time.monotonic() - start_time) * 1000, 2)

    return SimulationReport(
        id=report_id,
        prompt=request.prompt,
        type=sim_type,
        target_entity=resolved_name,
        executive_summary=summary,
        blast_radius_score=blast_radius,
        outage_details=outage_details,
        upgrade_details=upgrade_details,
        recovery_details=recovery_details,
        actionable_recommendations=recommendations,
        fork_graph=fork_id,
        execution_time_ms=duration_ms,
        created_at=time.time(),
    )
