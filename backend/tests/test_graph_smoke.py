"""FalkorDB smoke tests for ECHO — Software Failure Simulator.

Tests run on ISOLATED throwaway graphs (never touches the project graph).
Verifies: software-architecture MERGE, multi-hop dependency traversal,
fallback discovery, and graph-fork failure simulation.
"""

import uuid

import pytest

SMOKE_GRAPH = f"smoke_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def smoke(store, falkor_up):
    if not falkor_up:
        pytest.skip("FalkorDB not reachable")
    yield SMOKE_GRAPH
    try:
        store.graph(SMOKE_GRAPH).delete()
    except Exception:
        pass


def test_software_merge_idempotent_and_dependency_chain(store, smoke):
    """Insert microservices, databases, and third-party integrations; test multi-hop traversal."""
    seed = """
    MERGE (app:ClientApp {id: $app_id})
      SET app.name = 'Web Storefront', app.platform = 'web', app.active_users = 15000

    MERGE (ep:APIEndpoint {id: $ep_id})
      SET ep.path = '/api/v1/checkout', ep.method = 'POST'

    MERGE (c_svc:Service {id: $checkout_id})
      SET c_svc.name = 'checkout-service', c_svc.tier = 1, c_svc.status = 'healthy'

    MERGE (a_svc:Service {id: $auth_id})
      SET a_svc.name = 'auth-service', a_svc.tier = 1, a_svc.status = 'healthy'

    MERGE (p_svc:Service {id: $pay_id})
      SET p_svc.name = 'payment-service', p_svc.tier = 1, p_svc.status = 'healthy'

    MERGE (db:Database {id: $db_id})
      SET db.name = 'Auth PostgreSQL', db.type = 'postgresql', db.tier = 1

    MERGE (tp_primary:ThirdParty {id: $tp_pri_id})
      SET tp_primary.name = 'Stripe Payments', tp_primary.category = 'payment', tp_primary.tier = 1

    MERGE (tp_backup:ThirdParty {id: $tp_bak_id})
      SET tp_backup.name = 'PayPal Backup', tp_backup.category = 'payment', tp_backup.tier = 2

    MERGE (lib:Library {id: $lib_id})
      SET lib.name = 'crypto-jwt', lib.version = '2.4.0', lib.latest_version = '3.0.0'

    MERGE (tm:Team {id: $team_id})
      SET tm.name = 'Checkout & Orders Team', tm.slack_channel = '#team-checkout'

    MERGE (app)-[:CALLS]->(ep)
    MERGE (ep)-[:ROUTED_TO]->(c_svc)
    MERGE (c_svc)-[:CALLS]->(a_svc)
    MERGE (c_svc)-[:CALLS]->(p_svc)
    MERGE (a_svc)-[:CONNECTS_TO]->(db)
    MERGE (a_svc)-[:USES_LIBRARY]->(lib)
    MERGE (p_svc)-[:INTEGRATES_WITH]->(tp_primary)
    MERGE (tp_backup)-[:FALLBACK_FOR]->(tp_primary)
    MERGE (c_svc)-[:OWNED_BY]->(tm)
    """
    params = {
        "app_id": "app_web",
        "ep_id": "ep_checkout",
        "checkout_id": "svc_checkout",
        "auth_id": "svc_auth",
        "pay_id": "svc_payment",
        "db_id": "db_auth_pg",
        "tp_pri_id": "tp_stripe",
        "tp_bak_id": "tp_paypal",
        "lib_id": "lib_jwt",
        "team_id": "team_checkout",
    }

    # Run twice — must be strictly idempotent
    for _ in range(2):
        store.query(seed, params, graph=smoke)

    counts = store.ro_query(
        "MATCH (n) RETURN labels(n)[0] AS l, count(n) AS c ORDER BY l", graph=smoke
    ).result_set
    label_counts = {row[0]: row[1] for row in counts}
    assert label_counts == {
        "APIEndpoint": 1,
        "ClientApp": 1,
        "Database": 1,
        "Library": 1,
        "Service": 3,
        "Team": 1,
        "ThirdParty": 2,
    }

    # 1. Multi-hop call chain: what services are called downstream of checkout-service?
    downstream = store.ro_query(
        """
        MATCH (start:Service {id: 'svc_checkout'})-[:CALLS*1..3]->(target:Service)
        RETURN target.name ORDER BY target.name
        """,
        graph=smoke,
    ).result_set
    assert [row[0] for row in downstream] == ["auth-service", "payment-service"]

    # 2. Blast radius: what calls auth-service upstream?
    callers = store.ro_query(
        """
        MATCH (caller:Service)-[:CALLS*1..3]->(target:Service {id: 'svc_auth'})
        RETURN caller.name ORDER BY caller.name
        """,
        graph=smoke,
    ).result_set
    assert [row[0] for row in callers] == ["checkout-service"]

    # 3. Fallback recovery: does Stripe have an alternate provider configured?
    fallback = store.ro_query(
        """
        MATCH (backup:ThirdParty)-[:FALLBACK_FOR]->(primary:ThirdParty {id: 'tp_stripe'})
        RETURN backup.name
        """,
        graph=smoke,
    ).result_set
    assert fallback[0][0] == "PayPal Backup"


def test_fork_copy_and_service_failure_simulation(store, falkor_up):
    """Test: copy software architecture graph, simulate service outage on fork, verify live graph untouched."""
    if not falkor_up:
        pytest.skip("FalkorDB not reachable")

    src_graph = f"fork_src_{uuid.uuid4().hex[:8]}"
    fork_graph = f"fork_dst_{uuid.uuid4().hex[:8]}"

    try:
        # Seed the source graph with a microservice dependency chain
        store.query(
            """
            CREATE (api:Service {id: 'svc_api', name: 'api-gateway'})
            CREATE (auth:Service {id: 'svc_auth', name: 'auth-service'})
            CREATE (pay:Service {id: 'svc_pay', name: 'payment-service'})
            CREATE (api)-[:CALLS]->(auth)
            CREATE (api)-[:CALLS]->(pay)
            """,
            graph=src_graph,
        )

        # Copy live graph to isolated simulation fork
        store.graph(src_graph).copy(fork_graph)

        # Verify fork has the exact same 3 services
        fork_count = store.ro_query("MATCH (n:Service) RETURN count(n)", graph=fork_graph).result_set[0][0]
        assert fork_count == 3

        # Simulate failure: auth-service goes offline / removed on fork
        store.query("MATCH (s:Service {id: 'svc_auth'}) DETACH DELETE s", graph=fork_graph)

        # Fork now only has 2 services
        fork_after = store.ro_query("MATCH (n:Service) RETURN count(n)", graph=fork_graph).result_set[0][0]
        assert fork_after == 2

        # In fork: api-gateway now only has 1 healthy dependency
        fork_deps = store.ro_query(
            "MATCH (:Service {id: 'svc_api'})-[:CALLS]->(d:Service) RETURN d.id",
            graph=fork_graph,
        ).result_set
        assert [r[0] for r in fork_deps] == ["svc_pay"]

        # LIVE source graph must be 100% untouched (still 3 services, both dependencies present)
        live_count = store.ro_query("MATCH (n:Service) RETURN count(n)", graph=src_graph).result_set[0][0]
        assert live_count == 3
        live_deps = store.ro_query(
            "MATCH (:Service {id: 'svc_api'})-[:CALLS]->(d:Service) RETURN d.id ORDER BY d.id",
            graph=src_graph,
        ).result_set
        assert [r[0] for r in live_deps] == ["svc_auth", "svc_pay"]

    finally:
        for g in (src_graph, fork_graph):
            try:
                store.graph(g).delete()
            except Exception:
                pass


def test_ro_query_rejects_writes(store, falkor_up):
    if not falkor_up:
        pytest.skip("FalkorDB not reachable")
    tmp = f"ro_test_{uuid.uuid4().hex[:8]}"
    try:
        store.query("CREATE (:Tmp)", graph=tmp)
        with pytest.raises(Exception):
            store.ro_query("CREATE (:ShouldFail)", graph=tmp)
    finally:
        try:
            store.graph(tmp).delete()
        except Exception:
            pass
