# ConseQ Graph Algorithms and Cypher Queries

ConseQ stores software architecture in FalkorDB as a directed property graph. Its core analysis combines Cypher path traversal with application-level scoring; it does not implement custom GraphBLAS algorithms.

## Core algorithms

### 1. Multi-hop outage impact

Starting from a failed service, ConseQ follows incoming `CALLS` paths up to five hops to find upstream services that depend on it. For database and third-party failures, it first finds directly connected services through `CONNECTS_TO` or `INTEGRATES_WITH`, then traces their callers. Results include hop distance, service tier, and owner team.

```cypher
MATCH path = (caller:Service)-[:CALLS*1..5]->(target {id: $id})
WHERE caller.id <> $id
OPTIONAL MATCH (caller)-[:OWNED_BY]->(team:Team)
RETURN DISTINCT caller.id AS id, caller.name AS name,
       caller.tier AS tier, length(path) AS hops, team.name AS team
ORDER BY hops, tier
```

### 2. Customer and operational impact

The affected service set is mapped to API endpoints, client apps, active-user counts, and owning teams. ConseQ classifies a directly affected Tier 1 service as an outage and other affected services as degraded. Its blast-radius percentage is the affected service count divided by all services, capped at 100%.

```cypher
MATCH (ep:APIEndpoint)-[:ROUTED_TO]->(s:Service)
WHERE s.id IN $affected_ids
RETURN ep.id AS endpoint, ep.path AS path, s.id AS service
```

```cypher
MATCH (app:ClientApp)-[:CALLS]->(ep:APIEndpoint)
WHERE ep.id IN $endpoint_ids
RETURN app.name AS client, app.active_users AS active_users,
       collect(ep.path) AS affected_endpoints
```

### 3. Isolated what-if simulation

`ForkManager` copies the source named graph to a temporary `sim_<id>` graph. Failure mutations and impact queries run on that fork; the fork is deleted after use, with startup cleanup for orphaned simulation graphs. This keeps simulation writes away from the source graph.

```cypher
MATCH (n {id: $id}) SET n.status = 'offline'
```

### 4. Upgrade and recovery analysis

For a library upgrade, ConseQ finds services connected by `USES_LIBRARY`, checks whether the major version changes, and rates risk based on the change and dependent service tiers. It recommends rollout from lower-tier services toward Tier 1. Recovery analysis looks for registered `FALLBACK_FOR` edges and returns the configured backup and SLA.

```cypher
MATCH (s:Service)-[:USES_LIBRARY]->(l:Library)
WHERE l.id = $id
OPTIONAL MATCH (s)-[:OWNED_BY]->(t:Team)
RETURN s.id, s.name, s.tier, t.name AS team
ORDER BY s.tier DESC
```

```cypher
MATCH (backup)-[:FALLBACK_FOR]->(primary {id: $id})
RETURN backup.id, backup.name, labels(backup)[0] AS type,
       coalesce(backup.sla, 99.5) AS sla
```

### 5. Topology extraction and ingestion

Uploaded project files are parsed into typed nodes and dependency edges. Ingestion uses parameterized `UNWIND` batches with `MERGE` so matching node and edge records can be loaded idempotently into a dedicated project graph.

```cypher
UNWIND $rows AS row
MERGE (n:Service {id: row.id})
SET n += row
```

```cypher
UNWIND $rows AS row
MATCH (a {id: row.src}), (b {id: row.tgt})
MERGE (a)-[:CALLS]->(b)
```

## Supporting database features

- **Indexes and uniqueness constraints** support entity lookup and schema integrity.
- **Parameterized queries** keep supplied values separate from Cypher text; read-only analyses use the database client's read-only query path.
- **Graph statistics and health checks** report graph availability and basic node/edge counts.
- **Interactive topology view** receives bounded node and edge data from the graph for rendering in the frontend canvas.

Implementation: `backend/app/agent/tools.py`, `backend/app/services/fork.py`, `backend/app/services/ingest.py`, and `frontend/js/graph-visualizer.js`.
