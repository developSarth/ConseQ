"""Seed script for ECHO — AI-Powered Software Failure Simulator.

Populates FalkorDB with an enterprise e-commerce & fintech microservice architecture:
- 14 Microservices (Tier 1 core path, Tier 2 business features, Tier 3 support)
- 9 API Endpoints
- 6 Databases & Caches (Postgres, Mongo, Redis, Kafka)
- 5 Third-Party Providers (Stripe, PayPal, Twilio, SendGrid, Datadog)
- 4 Shared Libraries (crypto-jwt, fintech-payment-sdk, grpc-common, structured-logger)
- 4 Client Applications (Web, iOS, Android, B2B Partner API)
- 5 Engineering Teams with on-call leads and Slack channels
- Configured Fallback routes (PayPal as backup for Stripe, SendGrid as backup for Twilio)

Usage:
    python scripts/seed_software.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules import cleanly
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.falkor import GraphStore
from app.db.schema import ensure_schema

log = logging.getLogger("scripts.seed_software")


TEAMS = [
    ("team_identity", "Identity & Access Team", "#team-identity", "Sarah Chen"),
    ("team_checkout", "Checkout & Billing Team", "#team-checkout", "Marcus Vance"),
    ("team_catalog", "Product Catalog Team", "#team-catalog", "Priya Sharma"),
    ("team_platform", "Core Platform SRE Team", "#team-platform", "Alex Rivera"),
    ("team_logistics", "Fulfillment & Logistics Team", "#team-logistics", "Elena Rostova"),
]

LIBRARIES = [
    ("lib_jwt", "crypto-jwt", "2.4.1", "3.0.0", "python"),
    ("lib_payment_sdk", "fintech-payment-sdk", "1.2.0", "2.0.0", "python"),
    ("lib_grpc", "grpc-common-proto", "1.48.0", "1.52.0", "go"),
    ("lib_logger", "structured-logger", "4.1.0", "4.2.0", "typescript"),
]

DATABASES = [
    ("db_auth_pg", "Auth PostgreSQL", "postgresql", 1),
    ("db_order_pg", "Orders PostgreSQL", "postgresql", 1),
    ("db_catalog_mongo", "Catalog MongoDB", "mongodb", 2),
    ("db_inventory_pg", "Inventory PostgreSQL", "postgresql", 1),
    ("cache_redis_session", "Session Redis Cluster", "redis", 1),
    ("queue_order_kafka", "Order Event Stream (Kafka)", "kafka", 1),
]

THIRD_PARTIES = [
    ("tp_stripe", "Stripe Payments", "payment", 1, 99.99),
    ("tp_paypal", "PayPal Backup", "payment", 2, 99.95),
    ("tp_twilio", "Twilio SMS", "messaging", 2, 99.90),
    ("tp_sendgrid", "SendGrid Email", "email", 3, 99.50),
    ("tp_datadog", "Datadog APM", "observability", 3, 99.90),
]

SERVICES = [
    # id, name, tier, status, language
    ("svc_gateway", "api-gateway", 1, "healthy", "go"),
    ("svc_auth", "auth-service", 1, "healthy", "python"),
    ("svc_user", "user-service", 1, "healthy", "python"),
    ("svc_catalog", "catalog-service", 2, "healthy", "go"),
    ("svc_cart", "cart-service", 2, "healthy", "typescript"),
    ("svc_checkout", "checkout-service", 1, "healthy", "python"),
    ("svc_payment", "payment-service", 1, "healthy", "python"),
    ("svc_inventory", "inventory-service", 1, "healthy", "go"),
    ("svc_order", "order-service", 1, "healthy", "python"),
    ("svc_notification", "notification-service", 3, "healthy", "typescript"),
    ("svc_recommendation", "recommendation-service", 3, "healthy", "python"),
    ("svc_search", "search-service", 2, "healthy", "go"),
    ("svc_fraud", "fraud-detection-service", 1, "healthy", "python"),
    ("svc_shipping", "shipping-service", 2, "healthy", "go"),
]

ENDPOINTS = [
    # id, path, method, service_id
    ("ep_login", "/api/v1/auth/login", "POST", "svc_auth"),
    ("ep_verify_token", "/api/v1/auth/verify", "GET", "svc_auth"),
    ("ep_get_products", "/api/v1/catalog/items", "GET", "svc_catalog"),
    ("ep_search_products", "/api/v1/search", "GET", "svc_search"),
    ("ep_view_cart", "/api/v1/cart", "GET", "svc_cart"),
    ("ep_add_cart", "/api/v1/cart/items", "POST", "svc_cart"),
    ("ep_checkout_submit", "/api/v1/checkout/submit", "POST", "svc_checkout"),
    ("ep_process_payment", "/api/v1/payments/charge", "POST", "svc_payment"),
    ("ep_get_orders", "/api/v1/orders", "GET", "svc_order"),
]

CLIENT_APPS = [
    # id, name, platform, active_users
    ("app_web", "Web Storefront", "web", 45000),
    ("app_ios", "iOS Mobile App", "ios", 28000),
    ("app_android", "Android Mobile App", "android", 32000),
    ("app_partner_api", "B2B Partner Ingestion", "b2b", 1200),
]

# Service to Service RPC/HTTP dependencies: (caller, callee)
SERVICE_CALLS = [
    ("svc_gateway", "svc_auth"),
    ("svc_gateway", "svc_catalog"),
    ("svc_gateway", "svc_cart"),
    ("svc_gateway", "svc_checkout"),
    ("svc_gateway", "svc_order"),
    ("svc_gateway", "svc_search"),
    ("svc_checkout", "svc_auth"),
    ("svc_checkout", "svc_cart"),
    ("svc_checkout", "svc_fraud"),
    ("svc_checkout", "svc_payment"),
    ("svc_checkout", "svc_inventory"),
    ("svc_checkout", "svc_order"),
    ("svc_payment", "svc_fraud"),
    ("svc_order", "svc_inventory"),
    ("svc_order", "svc_shipping"),
    ("svc_order", "svc_notification"),
    ("svc_search", "svc_catalog"),
    ("svc_catalog", "svc_recommendation"),
]

# Service to Database connections: (service_id, database_id)
SERVICE_DATABASES = [
    ("svc_auth", "db_auth_pg"),
    ("svc_user", "db_auth_pg"),
    ("svc_cart", "cache_redis_session"),
    ("svc_order", "db_order_pg"),
    ("svc_order", "queue_order_kafka"),
    ("svc_inventory", "db_inventory_pg"),
    ("svc_catalog", "db_catalog_mongo"),
    ("svc_notification", "queue_order_kafka"),
]

# Service to ThirdParty integrations: (service_id, third_party_id)
SERVICE_THIRD_PARTIES = [
    ("svc_payment", "tp_stripe"),
    ("svc_notification", "tp_twilio"),
    ("svc_notification", "tp_sendgrid"),
    ("svc_gateway", "tp_datadog"),
]

# ThirdParty fallbacks: (backup_id, primary_id)
FALLBACK_ROUTES = [
    ("tp_paypal", "tp_stripe"),       # PayPal is configured fallback for Stripe
    ("tp_sendgrid", "tp_twilio"),     # SendGrid is email fallback if Twilio SMS fails
]

# Service to Library dependencies: (service_id, library_id)
SERVICE_LIBRARIES = [
    ("svc_auth", "lib_jwt"),
    ("svc_user", "lib_jwt"),
    ("svc_payment", "lib_payment_sdk"),
    ("svc_checkout", "lib_payment_sdk"),
    ("svc_gateway", "lib_grpc"),
    ("svc_catalog", "lib_grpc"),
    ("svc_cart", "lib_logger"),
    ("svc_notification", "lib_logger"),
]

# Service & Database ownership: (entity_id, team_id, is_db)
OWNERSHIPS = [
    ("svc_auth", "team_identity", False),
    ("svc_user", "team_identity", False),
    ("db_auth_pg", "team_identity", True),
    ("svc_checkout", "team_checkout", False),
    ("svc_payment", "team_checkout", False),
    ("svc_order", "team_checkout", False),
    ("db_order_pg", "team_checkout", True),
    ("svc_catalog", "team_catalog", False),
    ("svc_search", "team_catalog", False),
    ("svc_recommendation", "team_catalog", False),
    ("db_catalog_mongo", "team_catalog", True),
    ("svc_gateway", "team_platform", False),
    ("cache_redis_session", "team_platform", True),
    ("queue_order_kafka", "team_platform", True),
    ("svc_inventory", "team_logistics", False),
    ("svc_shipping", "team_logistics", False),
    ("db_inventory_pg", "team_logistics", True),
    ("svc_cart", "team_checkout", False),
    ("svc_fraud", "team_checkout", False),
    ("svc_notification", "team_platform", False),
]


def seed_database(store: GraphStore) -> None:
    """Idempotently seed the software architecture graph into FalkorDB."""
    log.info("Ensuring schema first...")
    ensure_schema(store)

    log.info("Seeding Teams...")
    for tid, name, slack, lead in TEAMS:
        store.query(
            """
            MERGE (t:Team {id: $id})
            SET t.name = $name, t.slack_channel = $slack, t.oncall_lead = $lead
            """,
            {"id": tid, "name": name, "slack": slack, "lead": lead},
        )

    log.info("Seeding Shared Libraries...")
    for lid, name, ver, l_ver, lang in LIBRARIES:
        store.query(
            """
            MERGE (l:Library {id: $id})
            SET l.name = $name, l.version = $ver, l.latest_version = $l_ver, l.language = $lang
            """,
            {"id": lid, "name": name, "ver": ver, "l_ver": l_ver, "lang": lang},
        )

    log.info("Seeding Databases...")
    for did, name, dtype, tier in DATABASES:
        store.query(
            """
            MERGE (d:Database {id: $id})
            SET d.name = $name, d.type = $type, d.tier = $tier
            """,
            {"id": did, "name": name, "type": dtype, "tier": tier},
        )

    log.info("Seeding Third-Party SaaS Providers...")
    for tpid, name, cat, tier, sla in THIRD_PARTIES:
        store.query(
            """
            MERGE (tp:ThirdParty {id: $id})
            SET tp.name = $name, tp.category = $cat, tp.tier = $tier, tp.sla = $sla
            """,
            {"id": tpid, "name": name, "cat": cat, "tier": tier, "sla": sla},
        )

    log.info("Seeding Microservices...")
    for sid, name, tier, status, lang in SERVICES:
        store.query(
            """
            MERGE (s:Service {id: $id})
            SET s.name = $name, s.tier = $tier, s.status = $status, s.language = $lang
            """,
            {"id": sid, "name": name, "tier": tier, "status": status, "lang": lang},
        )

    log.info("Seeding API Endpoints...")
    for epid, path, method, sid in ENDPOINTS:
        store.query(
            """
            MERGE (ep:APIEndpoint {id: $id})
            SET ep.path = $path, ep.method = $method, ep.service_id = $sid
            WITH ep
            MATCH (s:Service {id: $sid})
            MERGE (ep)-[:ROUTED_TO]->(s)
            """,
            {"id": epid, "path": path, "method": method, "sid": sid},
        )

    log.info("Seeding Client Applications...")
    for aid, name, platform, users in CLIENT_APPS:
        store.query(
            """
            MERGE (a:ClientApp {id: $id})
            SET a.name = $name, a.platform = $platform, a.active_users = $users
            """,
            {"id": aid, "name": name, "platform": platform, "users": users},
        )

    log.info("Wiring Client Apps to Ingress Endpoints...")
    # Web and Mobile call customer endpoints
    client_calls = [
        ("app_web", "ep_login"),
        ("app_web", "ep_get_products"),
        ("app_web", "ep_search_products"),
        ("app_web", "ep_view_cart"),
        ("app_web", "ep_add_cart"),
        ("app_web", "ep_checkout_submit"),
        ("app_web", "ep_get_orders"),
        ("app_ios", "ep_login"),
        ("app_ios", "ep_get_products"),
        ("app_ios", "ep_search_products"),
        ("app_ios", "ep_checkout_submit"),
        ("app_android", "ep_login"),
        ("app_android", "ep_get_products"),
        ("app_android", "ep_search_products"),
        ("app_android", "ep_checkout_submit"),
        ("app_partner_api", "ep_get_orders"),
        ("app_partner_api", "ep_checkout_submit"),
    ]
    for aid, epid in client_calls:
        store.query(
            """
            MATCH (a:ClientApp {id: $aid}), (ep:APIEndpoint {id: $epid})
            MERGE (a)-[:CALLS]->(ep)
            """,
            {"aid": aid, "epid": epid},
        )

    log.info("Wiring Service-to-Service CALLS edges...")
    for caller, callee in SERVICE_CALLS:
        store.query(
            """
            MATCH (c:Service {id: $caller}), (t:Service {id: $callee})
            MERGE (c)-[:CALLS]->(t)
            """,
            {"caller": caller, "callee": callee},
        )

    log.info("Wiring Service-to-Database CONNECTS_TO edges...")
    for sid, did in SERVICE_DATABASES:
        store.query(
            """
            MATCH (s:Service {id: $sid}), (d:Database {id: $did})
            MERGE (s)-[:CONNECTS_TO]->(d)
            """,
            {"sid": sid, "did": did},
        )

    log.info("Wiring Service-to-ThirdParty INTEGRATES_WITH edges...")
    for sid, tpid in SERVICE_THIRD_PARTIES:
        store.query(
            """
            MATCH (s:Service {id: $sid}), (tp:ThirdParty {id: $tpid})
            MERGE (s)-[:INTEGRATES_WITH]->(tp)
            """,
            {"sid": sid, "tpid": tpid},
        )

    log.info("Wiring ThirdParty Fallback routes (FALLBACK_FOR)...")
    for backup_id, primary_id in FALLBACK_ROUTES:
        store.query(
            """
            MATCH (backup:ThirdParty {id: $backup_id}), (primary:ThirdParty {id: $primary_id})
            MERGE (backup)-[:FALLBACK_FOR]->(primary)
            """,
            {"backup_id": backup_id, "primary_id": primary_id},
        )

    log.info("Wiring Service-to-Library USES_LIBRARY edges...")
    for sid, lid in SERVICE_LIBRARIES:
        store.query(
            """
            MATCH (s:Service {id: $sid}), (l:Library {id: $lid})
            MERGE (s)-[:USES_LIBRARY]->(l)
            """,
            {"sid": sid, "lid": lid},
        )

    log.info("Wiring Service and Database OWNED_BY edges...")
    for entity_id, team_id, is_db in OWNERSHIPS:
        label = "Database" if is_db else "Service"
        if not label.isidentifier():
            raise ValueError(f"Invalid label identifier: {label}")
        store.query(
            f"""
            MATCH (n:{label} {{id: $entity_id}}), (t:Team {{id: $team_id}})
            MERGE (n)-[:OWNED_BY]->(t)
            """,
            {"entity_id": entity_id, "team_id": team_id},
        )

    # Print summary of nodes seeded
    summary = store.ro_query(
        "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC"
    ).result_set
    rel_summary = store.ro_query(
        "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count ORDER BY count DESC"
    ).result_set

    log.info("=== Seed Complete! Nodes created: ===")
    for row in summary:
        log.info("  %s: %s", row[0], row[1])
    log.info("=== Relationships created: ===")
    for row in rel_summary:
        log.info("  %s: %s", row[0], row[1])


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("Connecting to FalkorDB for ECHO seeding: host=%s, graph=%s",
             settings.falkordb_host, settings.falkordb_graph)
    store = GraphStore(settings)
    if not store.connect():
        log.error("Could not connect to FalkorDB Cloud. Check credentials or network.")
        sys.exit(1)

    try:
        seed_database(store)
    finally:
        store.close()


if __name__ == "__main__":
    main()
