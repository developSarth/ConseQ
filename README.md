# ECHO — Software Architecture & Failure Simulator

> **Simulate cascading software failures, blast radius, and dependency upgrades on isolated in-memory graph forks before deploying to production.**

**Live demo:** [conseq.pages.dev](https://conseq.pages.dev/)
**Recorded demo:** [Watch the demo](https://youtu.be/eZdVMQogYg4)
**Track:** Agents with connected Data

---

## ⚡ Quickstart & Setup

### 1. Prerequisites
- **Python 3.10+**
- **FalkorDB** (FalkorDB Cloud or local Docker: `docker run -p 6379:6379 -it --rm falkordb/falkordb`)
- **Google Gemini API Key** (optional for natural-language intent parsing and report synthesis; fallback rule engine included)

### 2. Installation

```bash
# Clone repository
git clone https://github.com/developSarth/ConseQ.git
cd ConseQ

# Create and activate virtual environment
python -m venv .venv
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```ini
ENVIRONMENT=dev
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000"]

# FalkorDB Connection
FALKORDB_HOST=localhost
FALKORDB_PORT=6379
FALKORDB_USERNAME=default
FALKORDB_PASSWORD=
FALKORDB_SSL=false
FALKORDB_GRAPH=echo_software

# Simulation Limits
MAX_CONCURRENT_FORKS=5
FORK_TTL_MINUTES=30

# Gemini AI (Optional)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Seed Architecture Graph

Populate FalkorDB with the enterprise e-commerce & fintech microservice architecture:

```bash
python scripts/seed_software.py
```

### 5. Run the Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- **Interactive UI**: Open `frontend/index.html` in any browser (or serve via Live Server / `python -m http.server 3000` from `frontend/`).
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`
- **Readiness Probe**: `http://localhost:8000/health/ready`
- **Graph Topology**: `http://localhost:8000/graph/topology`

---

## 📊 Graph Data Model

ECHO models full-stack distributed systems as a directed labeled property graph in FalkorDB:

```
(ClientApp) ──[:CALLS]──▶ (APIEndpoint) ──[:ROUTED_TO]──▶ (Service)
                                                            │
    ┌──────────────────────┬──────────────────────┬─────────┴────────────┐
    ▼                      ▼                      ▼                      ▼
[:CALLS]              [:CONNECTS_TO]      [:INTEGRATES_WITH]      [:USES_LIBRARY]
    ▼                      ▼                      ▼                      ▼
(Service)              (Database)            (ThirdParty)            (Library)
    │                      │                      │
[:OWNED_BY]            [:OWNED_BY]          [:FALLBACK_FOR]
    ▼                      ▼                      ▼
 (Team)                 (Team)               (ThirdParty)
```

For the main traversals, impact queries, fork simulations, and ingestion patterns used by ConseQ, see [Graph Algorithms and Cypher Queries](docs/GRAPH_ALGORITHMS_AND_QUERIES.md).

### Node Labels

| Label | Primary Properties | Purpose |
|---|---|---|
| `Service` | `id, name, tier (1-3), status, language` | Microservices and backend components |
| `APIEndpoint` | `id, path, method, service_id` | Ingress HTTP/gRPC routes exposed to clients |
| `Database` | `id, name, type (pg, redis, mongo, kafka), tier` | Datastores, caches, and event streams |
| `ThirdParty` | `id, name, category, tier, sla` | External SaaS APIs & vendors (Stripe, Twilio) |
| `Library` | `id, name, version, latest_version, language` | Shared SDKs and dependencies (`crypto-jwt`) |
| `ClientApp` | `id, name, platform (web, ios, android), active_users` | Customer frontend applications |
| `Team` | `id, name, slack_channel, oncall_lead` | Engineering ownership and escalation targets |
| `SchemaMeta` | `id, version, domain` | Forward-only migration tracker |

### Relationship Edges

| Relationship | Pattern | Semantic Meaning |
|---|---|---|
| `CALLS` | `(ClientApp)-[:CALLS]->(APIEndpoint)` | Ingress client traffic to API gateway/routes |
| `ROUTED_TO` | `(APIEndpoint)-[:ROUTED_TO]->(Service)` | Endpoint routing to handling microservice |
| `CALLS` | `(Service)-[:CALLS]->(Service)` | Synchronous/asynchronous RPC or HTTP calls |
| `CONNECTS_TO` | `(Service)-[:CONNECTS_TO]->(Database)` | Datastore persistence & cache read/write |
| `INTEGRATES_WITH`| `(Service)-[:INTEGRATES_WITH]->(ThirdParty)` | External third-party API dependencies |
| `USES_LIBRARY` | `(Service)-[:USES_LIBRARY]->(Library)` | Package, shared library, and SDK dependencies |
| `FALLBACK_FOR` | `(ThirdParty)-[:FALLBACK_FOR]->(ThirdParty)` | Configured backup provider (e.g. PayPal $\rightarrow$ Stripe) |
| `OWNED_BY` | `(Service\|Database)-[:OWNED_BY]->(Team)` | Operational escalation and on-call alerting |

---

## 🔬 Core What-If Capabilities

1. **Failure Simulation (`POST /simulate`)**:
   - Clones live architecture into an isolated ephemeral graph fork (`g.copy()`).
   - Injects fault (`SET n.status = 'offline'`).
   - Traverses multi-hop dependency chains (`[:CALLS*1..5]`) to compute blast radius %, downstream caller degradation, broken routes, and affected customer user counts.
   - Cleans up simulation fork automatically.
2. **Library Upgrade Impact (`POST /simulate`)**:
   - Assesses dependency ripple effects across all services using a library (`[:USES_LIBRARY]`).
   - Identifies breaking major-version bumps and outputs a safe, reverse-dependency upgrade rollout order (Tier 3 $\rightarrow$ Tier 2 $\rightarrow$ Tier 1).
3. **Recovery & Fallback Routing (`POST /simulate`)**:
   - Discovers registered failover routes (`[:FALLBACK_FOR]`) and provides actionable mitigation playbooks.
