"""Phase 0 API tests for ECHO."""


def test_liveness_always_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "ECHO" in body["app"]
    assert "X-Request-ID" in r.headers


def test_request_id_is_echoed(client):
    r = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"


def test_readiness_shape(client):
    r = client.get("/health/ready")
    assert r.status_code in (200, 503)
    body = r.json()
    for key in ("status", "falkordb", "gemini_key_configured", "schema_version"):
        assert key in body


def test_graph_ping(client, falkor_up):
    r = client.get("/graph/ping")
    if falkor_up:
        assert r.status_code == 200
        assert r.json()["latency_ms"] >= 0
    else:
        assert r.status_code == 503
        assert r.json()["error"] == "graph_unavailable"


def test_graph_stats(client, falkor_up):
    r = client.get("/graph/stats")
    if falkor_up:
        assert r.status_code == 200
        body = r.json()
        assert "node_count" in body
        assert "edge_count" in body
        assert "labels" in body
    else:
        assert r.status_code == 503
