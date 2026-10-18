# ECHO — Backend Architecture Guide (Phase 0)

This guide documents the architecture, directory layout, core modules, FalkorDB schema design, and execution instructions for **ECHO — AI-Powered Software Failure Simulator**.

## Current behavior and limits

Failure simulations copy the configured graph, mark the selected entity offline in the copy, calculate impact against that copy, and clean it up after analysis. The simulation does not write to the configured graph. A failed fork does not fall back to querying the live graph. Upgrade impact and recovery are graph-based assessments; they do not currently mutate a fork or measure runtime impact. Recovery percentages are returned as `null` until a failover simulation measures them. Simulation audit records are not persisted. Topology responses are capped (up to 5,000 nodes and 10,000 links), and graph statistics are cached for five seconds. Fork capacity and cleanup tracking are process-local, so run one backend worker until shared coordination is added.

---

## 1. Directory Layout

```
GraphHacks/
├─ requirements.txt           FastAPI, FalkorDB, Google GenAI, Pytest
├─ .env                       Active environment variables (git-ignored)
├─ .env.example               Template with configuration schema
├─ ROADMAP.md                 High-level vision, workflows, and implementation phases
├─ docs/                      Architecture guides and API specifications
├─ scripts/
│  └─ seed_software.py        Realistic enterprise microservices seed script
├─ frontend/                  Phase 4 (React + Vite + interactive graph visualization)
└─ backend/
   ├─ pytest.ini
   ├─ app/
   │  ├─ __init__.py          Version string and app metadata
   │  ├─ main.py              App factory and async lifespan management
   │  ├─ core/
   │  │  ├─ config.py         Pydantic v2 typed settings (.env loader)
   │  │  ├─ logging.py        Async-safe contextual request logging
   │  │  ├─ middleware.py     Request ID tracking, timing, and error handling
   │  │  └─ system_checks.py  Runtime dependency probes
   │  ├─ db/
   │  │  ├─ falkor.py         GraphStore (resilient FalkorDB connection gateway)
   │  │  └─ schema.py         Indexes, constraints, and SchemaMeta bootstrap
   │  ├─ services/
   │  │  └─ fork.py           ForkManager (create, mutate, compare, destroy forks)
   │  ├─ api/
   │  │  ├─ deps.py           FastAPI dependency injection (store, fork_manager)
   │  │  └─ routes/
   │  │     ├─ health.py      Liveness (/health) and Readiness (/health/ready)
   │  │     └─ graph.py       FalkorDB ping and graph statistics (/graph/stats)
   │  ├─ schemas/
   │  │  ├─ health.py         Pydantic response models for health and graph stats
   │  │  └─ simulation.py     Schemas for simulation requests and reports
   │  └─ agent/               Phase 2 & 3 (Cypher cascade tools, Gemini intent parser)
   └─ tests/
      ├─ conftest.py          Fixtures for TestClient, GraphStore, and ForkManager
      ├─ test_health.py       Health and readiness route validation
      └─ test_graph_smoke.py  FalkorDB multi-hop traversal & fork simulation tests
```

---

## 2. Running Locally

```powershell
# 1. Activate Python virtual environment (Windows)
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials in .env
# Ensure FALKORDB_HOST, FALKORDB_PORT, FALKORDB_PASSWORD, and GEMINI_API_KEY are configured.

# 4. Run the Backend API server
cd backend
uvicorn app.main:app --reload --port 8000
# OpenAPI Docs:  http://localhost:8000/docs
# Liveness:      http://localhost:8000/health
# Readiness:     http://localhost:8000/health/ready
# Graph Stats:   http://localhost:8000/graph/stats

# 5. Run Test Suite
pytest -v
```

---

## 3. Core Modules Explained

### `app/core/config.py`: Centralized Typed Configuration
- Uses Pydantic `BaseSettings` reading from `.env`.
- Fields are strongly typed with bounds checking (`falkordb_port` between 1 and 65535, timeouts > 0).
- Secrets (`falkordb_password`, `gemini_api_key`) are wrapped in `SecretStr` to prevent accidental logging or leakage.
- Process-wide singleton cached via `@lru_cache`.

### `app/db/falkor.py`: `GraphStore` (The Database Gateway)
- Owns a pooled FalkorDB client and provides centralized query helpers.
- Automatic retries with exponential backoff on startup so the app can boot in graceful degraded mode even if the network is temporarily down.
- Enforces parameterized Cypher queries (`query()` and `ro_query()`) to prevent Cypher injection.
- Exposes `ro_query` which executes with read-only guarantees on the FalkorDB server.

### `app/services/fork.py`: `ForkManager` (The Simulation Engine)
- Implements the core simulation engine using FalkorDB named graph copying:
  1. `create_fork()`: Calls `live_graph.copy("sim_<uuid>")` to create an isolated graph sandbox.
  2. `apply_mutation()`: Applies simulated interventions (e.g. `MATCH (s:Service {id: $id}) DETACH DELETE s` or switching fallback routes) exclusively on the fork.
  3. Outage analysis executes against the fork; upgrade and recovery workflows currently use graph assessments without a fork.
  4. `destroy_fork()`: Deletes the simulation graph; failed deletes remain tracked for retry.
  5. TTL sweeping runs when creating a fork or checking capacity.

### `app/db/schema.py`: Software Architecture Schema & Constraints
- Automatically bootstrapped on application startup via `ensure_schema(store)`.
- Enforces unique constraints on `id` across all core software entities:
  - `Service`, `APIEndpoint`, `Database`, `ThirdParty`, `Library`, `ClientApp`, `Team`, `Simulation`, `SchemaMeta`.
- Creates and verifies range indexes and unique constraints before reporting schema readiness. Query latency depends on graph size, query shape, and FalkorDB deployment.
- Tracks `SchemaMeta` with forward-only versioning.

---

## 4. Graph Architecture: Software Failure & Blast Radius

### Node Types
- `Service`: Microservices and backend services (`id`, `name`, `tier`, `status`, `language`).
- `APIEndpoint`: Ingress HTTP/gRPC routes (`id`, `path`, `method`, `service_id`).
- `Database`: Persistent datastores and caches (`id`, `name`, `type`, `tier`).
- `ThirdParty`: SaaS vendors and external APIs (`id`, `name`, `category`, `tier`, `sla`).
- `Library`: Shared packages and SDKs (`id`, `name`, `version`, `latest_version`, `language`).
- `ClientApp`: User-facing clients (`id`, `name`, `platform`, `active_users`).
- `Team`: Engineering teams (`id`, `name`, `slack_channel`, `oncall_lead`).

### Edge Relationships
- `(ClientApp)-[:CALLS]->(APIEndpoint)`
- `(APIEndpoint)-[:ROUTED_TO]->(Service)`
- `(Service)-[:CALLS]->(Service)`
- `(Service)-[:CONNECTS_TO]->(Database)`
- `(Service)-[:INTEGRATES_WITH]->(ThirdParty)`
- `(Service)-[:USES_LIBRARY]->(Library)`
- `(ThirdParty)-[:FALLBACK_FOR]->(ThirdParty)`
- `(Service)-[:OWNED_BY]->(Team)`

---

## 5. The 3 What-If Workflows Supported

1. **Failure Simulation**:
   - Query: *"What happens if our authentication service goes offline?"*
   - Mechanism: Fork live graph -> mark `auth-service` offline -> execute blast-radius queries against the fork -> remove the fork -> report affected services, endpoints, clients, and owning teams. This reports graph impact; it does not contact PagerDuty or Slack.

2. **Change Impact Analysis**:
   - Query: *"What if I upgrade `crypto-jwt` to version 3?"*
   - Mechanism: Query `MATCH (s:Service)-[:USES_LIBRARY]->(lib:Library {name: 'crypto-jwt'})` -> identify all affected services, teams, and breaking contract risks before merging.

3. **Recovery Planning**:
   - Query: *"How can we keep checkout working if the payment provider (Stripe) fails?"*
   - Mechanism: Identify `(backup)-[:FALLBACK_FOR]->(stripe)` and produce mitigation guidance. No traffic reroute or recovery measurement is executed yet.
