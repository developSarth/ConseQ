# ECHO — AI-Powered Software Failure Simulator

> "What breaks if our auth service crashes?"  
> "What is the blast radius if Stripe goes down?"  
> "Can we safely upgrade this shared library to v3?"  
>
> **Product goal:** answer what-if questions against an isolated architecture graph before production changes.

## Current implementation status

The repository contains a working FastAPI/FalkorDB backend, a seed script, graph-based outage analysis, and assessment-only upgrade and recovery paths. Failure analysis runs on a temporary fork and removes it after the report is calculated; the configured live graph is not mutated by the simulation. Upgrade impact is inferred from dependency edges; recovery identifies configured fallback edges. Neither path currently executes a change on a fork or measures recovered traffic. Simulation audit nodes are not yet persisted. The frontend directory is empty. The project supports a single backend worker for fork-capacity enforcement; its limit and active-fork registry are process-local.

---

## 1. What is ECHO?

**ECHO** is an AI agent that simulates cascading software failures and architectural changes before you make them. 

Instead of guessing downstream impacts or finding out through PagerDuty alerts, ECHO:
1. Connects your software architecture (microservices, endpoints, databases, third-party providers, libraries, teams) to **FalkorDB**.
2. Forks the live architecture into an isolated, temporary graph in milliseconds using FalkorDB's `g.copy()`.
3. Simulates the failure, outage, or upgrade on the fork.
4. Traverses multi-hop dependency paths to calculate the **blast radius**, affected APIs, impacted customer applications, and responsible on-call teams.
5. Discovers configured **fallback routes** or degraded modes, simulates recovery interventions, and recommends the safest mitigation plan.

---

## 2. Core Capabilities & What Users Can Ask

### A. Failure Simulation
> *"What happens if our authentication service goes offline?"*
- Traverses multi-hop dependency chains (`[:CALLS*1..5]`).
- Discovers all upstream callers, broken endpoints, and affected client applications (Web, iOS, Android).
- Computes **Blast Radius Score** (% of architecture degraded) and groups impacted services by criticality Tier (Tier 1 mission-critical vs Tier 2/3).
- Identifies which engineering teams need to be notified immediately.

### B. Change Impact Analysis
> *"What if I upgrade `crypto-jwt` to version 3?"*
- Discovers all services and endpoints that depend on the library via `[:USES_LIBRARY]`.
- Evaluates breaking change risks across major version bumps.
- Generates a coordinated upgrade sequence and identifies shared regression risks across teams.

### C. Recovery Planning & Mitigation
> *"How can we keep checkout working if the payment provider (Stripe) fails?"*
- Queries the graph for configured `[:FALLBACK_FOR]` edges (e.g., secondary payment providers like PayPal or Adyen).
- Simulates automated failover on a fork: rewires the traffic to the fallback provider or degraded cash-on-delivery mode.
- Compares live vs simulated health metrics and outputs an actionable, step-by-step mitigation plan.

---

## 3. Architecture

```
User Prompt (Natural Language)
  "What if auth service goes offline?"
       │
       ▼
┌──────────────────────────────────────────────┐
│  INTENT PARSER (Gemini 2.5 Flash)            │
│  Extracts: target="svc_auth", action="FAIL"  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  FALKORDB FORK ENGINE                        │
│  1. g.copy("echo_software", "sim_<uuid>")    │  ← In-memory isolated graph copy
│  2. Apply mutation (DETACH DELETE / OFFLINE) │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  CASCADE & BLAST RADIUS ANALYZER (Cypher)    │
│  • trace_downstream_failures()               │  → Broken endpoints & client apps
│  • calculate_blast_radius()                  │  → Tier 1 vs Tier 2 disruption %
│  • find_impacted_teams()                     │  → On-call leads & Slack channels
│  • discover_fallbacks()                      │  → Alternative routes & backups
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  RECOVERY OPTIMIZER                          │
│  • Runs candidate mitigation on 2nd fork     │
│  • Compares recovery deltas against outage   │
│  • Selects minimum-loss path                 │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  GROUNDED ANSWER COMPOSER (Gemini)           │
│  Evidence-only report citing exact graph     │
│  nodes, impacted APIs, and recovery steps    │
└──────────────────────────────────────────────┘
```

---

## 4. Graph Schema

### Nodes
| Label | Key Properties | Purpose |
|---|---|---|
| `Service` | `id, name, tier (1-3), status, language, team_id` | Microservice or backend component |
| `APIEndpoint` | `id, path, method, service_id` | HTTP/gRPC route exposed to clients |
| `Database` | `id, name, type (pg, redis, mongo), tier` | Datastores, caches, message brokers |
| `ThirdParty` | `id, name, category (payment, sms, auth), tier, sla` | External SaaS APIs & vendors |
| `Library` | `id, name, version, latest_version, language` | Shared libraries, SDKs, packages |
| `ClientApp` | `id, name, platform (web, ios, android), active_users`| User-facing frontend clients |
| `Team` | `id, name, slack_channel, oncall_lead` | Engineering ownership & alerting |
| `Simulation` | `id, fork_graph, intervention_type, target, status` | Reserved for future persistent audit tracking |
| `SchemaMeta` | `id, version, domain` | Forward-only migration tracker |

### Edges
| Relationship | Description |
|---|---|
| `(ClientApp)-[:CALLS]->(APIEndpoint)` | Client traffic ingress point |
| `(APIEndpoint)-[:ROUTED_TO]->(Service)` | Endpoint implementation routing |
| `(Service)-[:CALLS]->(Service)` | Synchronous/asynchronous RPC or HTTP calls |
| `(Service)-[:CONNECTS_TO]->(Database)` | Datastore persistence & cache read/write |
| `(Service)-[:INTEGRATES_WITH]->(ThirdParty)` | External vendor API dependencies |
| `(Service)-[:USES_LIBRARY]->(Library)` | Package and SDK dependencies |
| `(ThirdParty)-[:FALLBACK_FOR]->(ThirdParty)` | Redundant secondary vendor / failover route |
| `(Service)-[:FALLBACK_FOR]->(Service)` | Degraded service fallback path |
| `(Service)-[:OWNED_BY]->(Team)` | Service ownership and escalation |
| `(Database)-[:OWNED_BY]->(Team)` | Database administrative ownership |

---

## 5. FalkorDB Superpowers Utilized

| FalkorDB Feature | How ECHO Uses It |
|---|---|
| **Named Graphs & `g.copy()`** | Isolated graph copies for what-if simulation forks |
| **Multi-Hop Cypher (`*1..5`)** | Multi-tier dependency propagation and blast radius detection |
| **GraphBLAS Sparse Matrix Engine** | Sub-millisecond graph query speed even with deep dependency trees |
| **Dual-Graph Delta Queries** | Side-by-side comparison of live vs simulated system health |
| **Idempotent MERGE & Mutate** | Fast failure injection without corrupting live metadata |
| **Native Range & Unique Indexes** | Instant service lookup by ID, tier, and status |

---

## 6. Project Directory Structure

```
d:/nodewave/GraphHacks/
├── .env                          # Local credentials (FalkorDB Cloud, Gemini)
├── .env.example                  # Sanitized template
├── ROADMAP.md                    # This document
├── requirements.txt              # FastAPI, FalkorDB, Google GenAI, Pytest
├── scripts/
│   └── seed_software.py          # Realistic e-commerce microservices architecture
├── backend/
│   ├── pytest.ini
│   ├── app/
│   │   ├── __init__.py           # ECHO version & package metadata
│   │   ├── main.py               # FastAPI app factory & lifespan
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic v2 BaseSettings
│   │   │   ├── logging.py        # Structured logging
│   │   │   ├── middleware.py     # Request IDs, timing, error mapping
│   │   │   └── system_checks.py  # Runtime connectivity verification
│   │   ├── db/
│   │   │   ├── falkor.py         # GraphStore client with retry/reconnect
│   │   │   └── schema.py         # Indexes, constraints, SchemaMeta
│   │   ├── services/
│   │   │   └── fork.py           # ForkManager (create, mutate, compare, destroy)
│   │   ├── schemas/
│   │   │   ├── health.py         # Health & stats responses
│   │   │   └── simulation.py     # Simulation request & report schemas
│   │   ├── agent/
│   │   │   ├── tools.py          # Cypher cascade & blast radius tools
│   │   │   ├── parser.py         # Gemini intent parser
│   │   │   └── runner.py         # Simulation orchestrator & reporter
│   │   └── api/
│   │       ├── deps.py           # Dependency injection (store, fork_mgr)
│   │       └── routes/
│   │           ├── health.py     # /health/live, /health/ready
│   │           ├── graph.py      # /graph/stats, /graph/topology
│   │           └── simulate.py   # /simulate/failure, /simulate/upgrade, /simulate/mitigate
│   └── tests/
│       ├── conftest.py           # Pytest fixtures
│       ├── test_health.py        # Health endpoint unit tests
│       └── test_graph_smoke.py   # Software dependency smoke tests
└── frontend/                     # React + Vite interactive UI
```

---

## 7. Phased Roadmap

### Phase 0 — Foundation ✅ (Complete)
- [x] FastAPI skeleton with health/readiness probes and correlation IDs
- [x] FalkorDB Cloud integration with auto-retry and connection resilience
- [x] Software architecture schema bootstrap (indexes, constraints, SchemaMeta)
- [x] In-memory graph fork engine (`create_fork`, `apply_mutation`, `compare`, `destroy_fork`)
- [x] Unit and smoke tests tuned for software dependencies

### Phase 1 — Architecture Seed Dataset 🔨
- [x] Add `scripts/seed_software.py` with an e-commerce microservice graph (14 services, 6 datastores/caches, 5 providers, 4 libraries, 4 clients, and 5 teams):
  - Services include `api-gateway`, `auth-service`, `checkout-service`, `payment-service`, `inventory-service`, `order-service`, and `catalog-service`.
  - Datastores include PostgreSQL, MongoDB, Redis, and Kafka nodes.
  - Providers include Stripe, PayPal, Twilio, SendGrid, and Datadog; PayPal is linked as a Stripe fallback.
  - Shared libraries include `crypto-jwt`, `fintech-payment-sdk`, `grpc-common-proto`, and `structured-logger`.

### Phase 2 — Cypher Cascade Tools
- [x] `trace_outage_blast_radius(entity_id)`: Find callers, endpoints, affected apps, and teams (analysis runs on a fork for outage simulations)
- [x] `trace_library_upgrade_impact(library_name, target_version)`: Assess dependent services and teams; does not execute an upgrade
- [x] `find_recovery_paths(failing_node_id)`: Look up `FALLBACK_FOR` edges and recommend degraded alternatives; does not execute failover
- [ ] `simulate_failover(primary_id, backup_id)`: Reroute traffic on fork and calculate restored availability

### Phase 3 — Agent Loop with Gemini
- [x] Intent classification for outage, upgrade impact, and recovery (Gemini with deterministic fallback)
- [x] Tool execution pipeline for forked outages and graph-based upgrade/recovery assessments
- [x] Report generator using graph-derived metrics and a deterministic fallback summary

### Phase 4 — Frontend Visualizer
- [ ] Split-view dashboard: System Architecture Topology + Live Simulation Canvas
- [ ] Blast radius red-alert highlighting on impacted nodes
- [ ] Interactive "What If?" prompt bar with suggested one-click scenarios
- [ ] Side-by-side recovery comparison card

### Phase 5 — EC2 Cloud Deployment
- [ ] Systemd service setup for FastAPI
- [ ] Nginx reverse proxy + static frontend hosting
- [ ] End-to-end cloud smoke verification
