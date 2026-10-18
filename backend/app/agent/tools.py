"""Cypher cascade and blast radius tools for ECHO software failure simulations.

Every tool queries FalkorDB using parameterised Cypher statements and returns
strongly-typed Pydantic result structures.
"""

from __future__ import annotations

import logging
from typing import Any

from app.db.falkor import GraphStore
from app.schemas.simulation import (
    ClientImpact,
    EndpointImpact,
    OutageSimulationResult,
    RecoveryPlanResult,
    ServiceImpact,
    TeamAlert,
    TopologyLink,
    TopologyNode,
    TopologyResponse,
    UpgradeImpactResult,
)

log = logging.getLogger("app.agent.tools")


def resolve_target_entity(
    store: GraphStore, query_str: str, graph: str | None = None, *, exact_only: bool = False
) -> dict[str, Any] | None:
    """Fuzzy-matches a service/thirdparty/library name or ID to an exact node."""
    norm = query_str.strip().lower().replace(" ", "-").replace("_", "-")
    clean_kw = query_str.strip().lower()

    # Canonical alias dictionary for natural-language prompts
    ALIASES = {
        "api key": "svc_gateway",
        "api-key": "svc_gateway",
        "api_key": "svc_gateway",
        "api keys": "svc_gateway",
        "apikey": "svc_gateway",
        "api-gateway": "svc_gateway",
        "api gateway": "svc_gateway",
        "gateway": "svc_gateway",
        "ingress": "svc_gateway",
        "routing": "svc_gateway",
        "auth": "svc_auth",
        "auth-service": "svc_auth",
        "authentication": "svc_auth",
        "login": "svc_auth",
        "tokens": "svc_auth",
        "jwt": "lib_jwt",
        "crypto-jwt": "lib_jwt",
        "payment": "svc_payment",
        "payments": "svc_payment",
        "payment-service": "svc_payment",
        "stripe": "tp_stripe",
        "paypal": "tp_paypal",
        "cart": "svc_cart",
        "cart-service": "svc_cart",
        "checkout": "svc_checkout",
        "checkout-service": "svc_checkout",
        "order": "svc_order",
        "orders": "svc_order",
        "order-service": "svc_order",
        "order db": "db_order_pg",
        "orders db": "db_order_pg",
        "postgres": "db_order_pg",
        "redis": "cache_redis_session",
        "session": "cache_redis_session",
        "cache": "cache_redis_session",
        "inventory": "svc_inventory",
        "inventory-service": "svc_inventory",
        "user": "svc_user",
        "user-service": "svc_user",
        "catalog": "svc_catalog",
        "catalog-service": "svc_catalog",
        "search": "svc_search",
        "search-service": "svc_search",
        "notification": "svc_notification",
        "shipping": "svc_shipping",
        "fraud": "svc_fraud",
        "kafka": "queue_order_kafka",
        "twilio": "tp_twilio",
        "sendgrid": "tp_sendgrid",
        "datadog": "tp_datadog",
    }

    alias_target_id = ALIASES.get(clean_kw) or ALIASES.get(norm)
    lookup_id = alias_target_id or query_str.strip()

    # Exact indexed IDs are the common path; exact names are next.
    exact_id = store.ro_query(
        """MATCH (n) WHERE (n:Service OR n:ThirdParty OR n:Library OR n:Database)
        AND n.id = $id
        RETURN labels(n)[0], n.id, coalesce(n.name, n.id), coalesce(n.tier, 2), coalesce(n.status, 'healthy')""",
        {"id": lookup_id}, graph=graph,
    ).result_set
    if exact_id:
        row = exact_id[0]
        return {"label": row[0], "id": row[1], "name": row[2], "tier": row[3], "status": row[4]}

    if exact_only:
        return None

    exact_name = store.ro_query(
        """MATCH (n) WHERE (n:Service OR n:ThirdParty OR n:Library OR n:Database)
        AND toLower(n.name) = $name
        RETURN labels(n)[0], n.id, coalesce(n.name, n.id), coalesce(n.tier, 2), coalesce(n.status, 'healthy')
        LIMIT 2""",
        {"name": clean_kw}, graph=graph,
    ).result_set
    if len(exact_name) == 1:
        row = exact_name[0]
        return {"label": row[0], "id": row[1], "name": row[2], "tier": row[3], "status": row[4]}

    if len(clean_kw) < 3:
        return None
    cypher = """
    MATCH (n)
    WHERE (n:Service OR n:ThirdParty OR n:Library OR n:Database)
      AND (toLower(n.id) CONTAINS $norm OR toLower(n.name) CONTAINS $name)
    RETURN labels(n)[0] AS label, n.id AS id, n.name AS name,
           coalesce(n.tier, 2) AS tier, coalesce(n.status, 'healthy') AS status
    LIMIT 2
    """
    res = store.ro_query(cypher, {"norm": norm, "name": clean_kw}, graph=graph).result_set
    if len(res) == 1:
        return {
            "label": res[0][0],
            "id": res[0][1],
            "name": res[0][2] or res[0][1],
            "tier": res[0][3],
            "status": res[0][4],
        }
    if len(res) > 1:
        log.info("Target query '%s' matched multiple entities; require a more specific target", query_str)
    return None


def trace_outage_blast_radius(
    store: GraphStore, target_id: str, graph: str | None = None
) -> OutageSimulationResult:
    """Calculates the multi-hop cascading blast radius of an outage at target_id.

    Traverses:
    1. Direct & transitive upstream callers (Service)-[:CALLS*1..5]->(target)
    2. Endpoints routed to target or callers
    3. ClientApps calling those endpoints
    4. Teams owning the impacted services
    """
    # 1. Resolve target entity details
    info_query = """
    MATCH (t {id: $id})
    RETURN labels(t)[0] AS label, coalesce(t.name, t.id) AS name, coalesce(t.tier, 1) AS tier
    """
    t_res = store.ro_query(info_query, {"id": target_id}, graph=graph).result_set
    if t_res:
        t_label, t_name, t_tier = t_res[0][0], t_res[0][1], t_res[0][2]
    else:
        t_label, t_name, t_tier = "Service", target_id, 1

    # 2. Find all upstream calling services (multi-hop)
    upstream_query = """
    MATCH path = (caller:Service)-[:CALLS*1..5]->(target {id: $id})
    WHERE caller.id <> $id
    OPTIONAL MATCH (caller)-[:OWNED_BY]->(team:Team)
    RETURN DISTINCT caller.id AS id, coalesce(caller.name, caller.id) AS name, coalesce(caller.tier, 2) AS tier,
           length(path) AS hops, team.name AS team_name
    ORDER BY hops ASC, tier ASC
    """
    callers = store.ro_query(upstream_query, {"id": target_id}, graph=graph).result_set

    # Add direct dependencies for infrastructure/provider outages, then trace
    # each affected service's upstream callers through the service graph.
    if t_label in ("ThirdParty", "Database"):
        rel = "INTEGRATES_WITH" if t_label == "ThirdParty" else "CONNECTS_TO"
        direct_callers = store.ro_query(
            f"""
            MATCH (caller:Service)-[:{rel}]->(target {{id: $id}})
            OPTIONAL MATCH (caller)-[:OWNED_BY]->(team:Team)
            RETURN caller.id AS id, coalesce(caller.name, caller.id) AS name, coalesce(caller.tier, 2) AS tier,
                   1 AS hops, team.name AS team_name
            """,
            {"id": target_id},
            graph=graph,
        ).result_set
        direct_service_ids = list({row[0] for row in direct_callers})
        callers = list(callers) + list(direct_callers)
        if direct_service_ids:
            transitive = store.ro_query(
                """
                MATCH path = (caller:Service)-[:CALLS*1..5]->(direct:Service)
                WHERE direct.id IN $direct_ids AND caller.id <> direct.id
                OPTIONAL MATCH (caller)-[:OWNED_BY]->(team:Team)
                RETURN DISTINCT caller.id AS id, coalesce(caller.name, caller.id) AS name,
                       coalesce(caller.tier, 2) AS tier,
                       length(path) + 1 AS hops, team.name AS team_name
                ORDER BY hops ASC, tier ASC
                """,
                {"direct_ids": direct_service_ids}, graph=graph,
            ).result_set
            callers = list(callers) + list(transitive)

    impacted_services: list[ServiceImpact] = []
    seen_services: set[str] = set()

    target_is_service = t_label == "Service"
    tier1_down = 1 if target_is_service and t_tier == 1 else 0
    tier2_down = 1 if target_is_service and t_tier == 2 else 0
    tier3_down = 1 if target_is_service and t_tier == 3 else 0

    for row in callers:
        sid, sname, stier, hops, team_name = row[0], row[1], row[2], row[3], row[4]
        if sid not in seen_services:
            seen_services.add(sid)
            impact_level = "outage" if stier == 1 and hops == 1 else "degraded"
            if stier == 1:
                tier1_down += 1
            elif stier == 2:
                tier2_down += 1
            elif stier == 3:
                tier3_down += 1
            impacted_services.append(
                ServiceImpact(
                    id=sid,
                    name=sname,
                    tier=stier,
                    impact=impact_level,
                    hops_from_target=hops,
                    team_name=team_name,
                )
            )

    all_affected_ids = list(seen_services | {target_id})

    # 3. Find broken endpoints
    broken_ep_query = """
    MATCH (ep:APIEndpoint)-[:ROUTED_TO]->(s:Service)
    WHERE s.id IN $affected_ids
    RETURN ep.id AS id, coalesce(ep.path, ep.id) AS path,
           coalesce(ep.method, 'UNKNOWN') AS method, s.id AS service_id
    """
    ep_res = store.ro_query(broken_ep_query, {"affected_ids": all_affected_ids}, graph=graph).result_set
    broken_endpoints: list[EndpointImpact] = [
        EndpointImpact(
            id=r[0],
            path=r[1],
            method=r[2],
            status="broken" if r[3] == target_id else "degraded",
            service_id=r[3],
        )
        for r in ep_res
    ]
    broken_ep_ids = [ep.id for ep in broken_endpoints]

    # 4. Find impacted client applications
    client_query = """
    MATCH (app:ClientApp)-[:CALLS]->(ep:APIEndpoint)
    WHERE ep.id IN $ep_ids
    RETURN app.id AS id, coalesce(app.name, app.id) AS name,
           coalesce(app.platform, 'unknown') AS platform,
           coalesce(app.active_users, 0) AS active_users, collect(DISTINCT ep.path) AS endpoints
    """
    client_res = store.ro_query(client_query, {"ep_ids": broken_ep_ids}, graph=graph).result_set
    impacted_clients: list[ClientImpact] = [
        ClientImpact(
            id=r[0],
            name=r[1],
            platform=r[2],
            active_users=r[3],
            affected_endpoints=r[4],
        )
        for r in client_res
    ]

    # 5. Find impacted teams to alert
    teams_query = """
    MATCH (target {id: $id})-[:OWNED_BY]->(t:Team)
    RETURN t.id AS id, coalesce(t.name, t.id) AS name, coalesce(t.slack_channel, '') AS slack,
           coalesce(t.oncall_lead, '') AS lead,
           'Primary owner of failing entity' AS reason
    UNION
    MATCH (s:Service)-[:OWNED_BY]->(t:Team)
    WHERE s.id IN $affected_ids AND s.id <> $id
    RETURN t.id AS id, coalesce(t.name, t.id) AS name, coalesce(t.slack_channel, '') AS slack,
           coalesce(t.oncall_lead, '') AS lead,
           'Downstream calling service degraded' AS reason
    """
    team_res = store.ro_query(teams_query, {"id": target_id, "affected_ids": all_affected_ids}, graph=graph).result_set
    impacted_teams: list[TeamAlert] = []
    seen_teams: set[str] = set()
    for r in team_res:
        if r[0] and r[0] not in seen_teams:
            seen_teams.add(r[0])
            impacted_teams.append(
                TeamAlert(
                    id=r[0],
                    name=r[1],
                    slack_channel=r[2],
                    oncall_lead=r[3],
                    reason=r[4],
                )
            )

    # 6. Calculate total services for blast radius score
    total_svc_res = store.ro_query("MATCH (s:Service) RETURN count(s)", graph=graph).result_set
    total_services = total_svc_res[0][0] if total_svc_res else 1
    affected_service_count = len(impacted_services) + (1 if target_is_service else 0)
    blast_radius = min(100.0, round((affected_service_count / max(total_services, 1)) * 100.0, 1))

    return OutageSimulationResult(
        target_id=target_id,
        target_name=t_name,
        target_type=t_label,
        blast_radius_percent=blast_radius,
        tier1_services_down=tier1_down,
        tier2_services_down=tier2_down,
        tier3_services_down=tier3_down,
        impacted_services=impacted_services,
        broken_endpoints=broken_endpoints,
        impacted_clients=impacted_clients,
        impacted_teams=impacted_teams,
    )


def trace_library_upgrade_impact(
    store: GraphStore, library_name: str, target_version: str, graph: str | None = None
) -> UpgradeImpactResult:
    """Discovers all services and teams affected by upgrading a shared library."""
    lib_query = """
    MATCH (l:Library)
    WHERE toLower(l.name) = toLower($name) OR toLower(l.id) = toLower($name)
    RETURN l.id AS id, coalesce(l.name, l.id) AS name,
           coalesce(l.version, 'unknown') AS version, l.latest_version AS latest_version
    """
    res = store.ro_query(lib_query, {"name": library_name}, graph=graph).result_set
    if not res:
        from app.core.middleware import TargetNotFoundError
        raise TargetNotFoundError(f"Library '{library_name}' was not found.")
    lib_id, lib_name, cur_ver = res[0][0], res[0][1], res[0][2]

    # Check major breaking version bump (safe for unparseable versions)
    try:
        cur_major = int(cur_ver.split(".")[0].replace("v", ""))
    except (ValueError, IndexError):
        log.warning("Unparseable current version '%s' for library '%s'; assuming major bump", cur_ver, lib_name)
        cur_major = -1
    try:
        target_major = int(target_version.split(".")[0].replace("v", ""))
    except (ValueError, IndexError):
        log.warning("Unparseable target version '%s'; assuming major bump", target_version)
        target_major = -2
    is_major = cur_major != target_major

    # Dependent services and their teams
    deps_query = """
    MATCH (s:Service)-[:USES_LIBRARY]->(l:Library)
    WHERE l.id = $id OR toLower(l.name) = toLower($name)
    OPTIONAL MATCH (s)-[:OWNED_BY]->(t:Team)
    RETURN s.id AS id, coalesce(s.name, s.id) AS name, coalesce(s.tier, 2) AS tier,
           coalesce(s.language, 'unknown') AS language,
           t.id AS team_id, t.name AS team_name,
           coalesce(t.slack_channel, '') AS slack, coalesce(t.oncall_lead, '') AS lead
    ORDER BY s.tier DESC
    """
    deps_res = store.ro_query(deps_query, {"id": lib_id, "name": lib_name}, graph=graph).result_set

    dependent_services: list[dict[str, Any]] = []
    teams: list[TeamAlert] = []
    seen_teams: set[str] = set()

    for r in deps_res:
        dependent_services.append(
            {"id": r[0], "name": r[1], "tier": r[2], "language": r[3], "team": r[5]}
        )
        if r[4] and r[4] not in seen_teams:
            seen_teams.add(r[4])
            teams.append(
                TeamAlert(
                    id=r[4],
                    name=r[5],
                    slack_channel=r[6],
                    oncall_lead=r[7],
                    reason=f"Service '{r[1]}' uses library '{lib_name}'",
                )
            )

    has_tier1 = any(s["tier"] == 1 for s in dependent_services)
    if is_major and has_tier1:
        risk_level = "CRITICAL"
    elif is_major:
        risk_level = "HIGH"
    elif has_tier1:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Recommended upgrade order: Tier 3 -> Tier 2 -> Tier 1 (reverse dependency risk)
    order = [s["name"] for s in dependent_services]

    return UpgradeImpactResult(
        library_id=lib_id,
        library_name=lib_name,
        current_version=cur_ver,
        target_version=target_version,
        is_major_breaking_bump=is_major,
        dependent_services=dependent_services,
        dependent_teams=teams,
        risk_level=risk_level,
        recommended_upgrade_order=order,
    )


def find_recovery_paths(
    store: GraphStore, failing_id: str, graph: str | None = None
) -> RecoveryPlanResult:
    """Discovers configured fallbacks (FALLBACK_FOR) and degraded recovery strategies."""
    info_query = """
    MATCH (t {id: $id})
    RETURN coalesce(t.name, t.id) AS name
    """
    t_res = store.ro_query(info_query, {"id": failing_id}, graph=graph).result_set
    failing_name = t_res[0][0] if t_res else failing_id

    # Find fallback provider or service
    fallback_query = """
    MATCH (backup)-[:FALLBACK_FOR]->(primary {id: $id})
        RETURN backup.id AS id, coalesce(backup.name, backup.id) AS name, labels(backup)[0] AS type,
           coalesce(backup.sla, 99.5) AS sla
    """
    fb_res = store.ro_query(fallback_query, {"id": failing_id}, graph=graph).result_set

    if fb_res:
        fb_id, fb_name, fb_type, fb_sla = fb_res[0][0], fb_res[0][1], fb_res[0][2], fb_res[0][3]
        steps = [
            f"1. Activate circuit breaker for primary provider '{failing_name}'.",
            f"2. Dynamically re-route egress calls to registered fallback '{fb_name}'.",
            f"3. Verify idempotency tokens and retry headers on '{fb_name}'.",
            f"4. Monitor error budget on '{fb_name}' (SLA target: {fb_sla}%).",
            "5. Re-enable traffic to primary in canary increments (5% -> 25% -> 100%) once health checks pass.",
        ]
        return RecoveryPlanResult(
            failing_entity_id=failing_id,
            failing_entity_name=failing_name,
            primary_provider=failing_name,
            fallback_provider=fb_name,
            fallback_available=True,
            estimated_recovery_rate=None,
            mitigation_steps=steps,
            degraded_mode_strategy="Automated active-passive vendor failover with circuit breaking.",
        )
    else:
        steps = [
            f"1. No active standby fallback found for '{failing_name}'.",
            "2. Activate degraded fallback mode: serve stale cached data where read-only traffic permits.",
            "3. Enqueue asynchronous write mutations to durable queue with backoff.",
            "4. Page owning team for emergency manual intervention.",
        ]
        return RecoveryPlanResult(
            failing_entity_id=failing_id,
            failing_entity_name=failing_name,
            primary_provider=failing_name,
            fallback_provider=None,
            fallback_available=False,
            estimated_recovery_rate=None,
            mitigation_steps=steps,
            degraded_mode_strategy="Cache-only degraded mode with asynchronous queue buffering.",
        )


def get_topology_graph(
    store: GraphStore, graph: str | None = None, affected_ids: set[str] | None = None,
    node_limit: int = 1000, edge_limit: int = 2500,
) -> TopologyResponse:
    """Returns all graph nodes and edges structured for force-directed visualizers."""
    aff = affected_ids or set()
    node_query = """
    MATCH (n)
    WHERE (n:Service OR n:APIEndpoint OR n:Database OR n:ThirdParty OR n:Library OR n:ClientApp)
      AND n.id IS NOT NULL
    RETURN n.id AS id, coalesce(n.name, n.path, n.id) AS name, labels(n)[0] AS label,
           coalesce(n.tier, 2) AS tier, coalesce(n.status, 'healthy') AS status,
           n.category AS category, n.platform AS platform
    """
    node_query += "\nLIMIT $limit"
    n_res = store.ro_query(node_query, {"limit": node_limit}, graph=graph).result_set

    nodes = [
        TopologyNode(
            id=r[0],
            name=r[1],
            label=r[2],
            tier=r[3],
            status="offline" if r[0] in aff else r[4],
            category=r[5],
            platform=r[6],
            is_affected=(r[0] in aff),
        )
        for r in n_res
    ]

    edge_query = """
    MATCH (source)-[r]->(target)
    WHERE (source:Service OR source:APIEndpoint OR source:Database OR source:ThirdParty OR source:Library OR source:ClientApp)
      AND (target:Service OR target:APIEndpoint OR target:Database OR target:ThirdParty OR target:Library OR target:ClientApp)
      AND source.id IS NOT NULL AND target.id IS NOT NULL
      AND source.id IN $node_ids AND target.id IN $node_ids
    RETURN source.id AS source, target.id AS target, type(r) AS type
    """
    edge_query += "\nLIMIT $limit"
    e_res = store.ro_query(
        edge_query,
        {"limit": edge_limit, "node_ids": [node.id for node in nodes]},
        graph=graph,
    ).result_set

    links = [
        TopologyLink(
            source=r[0],
            target=r[1],
            type=r[2],
            is_broken=(r[0] in aff or r[1] in aff),
        )
        for r in e_res
    ]

    return TopologyResponse(
        nodes=nodes,
        links=links,
        total_nodes=len(nodes),
        total_links=len(links),
        truncated=len(n_res) >= node_limit or len(e_res) >= edge_limit,
    )
