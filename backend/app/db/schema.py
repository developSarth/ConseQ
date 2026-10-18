"""FalkorDB schema bootstrap for ECHO — Software Architecture & Failure Simulator.

Creates all indexes and constraints needed for the software dependency graph.
Idempotent: safe to call on every startup. Skips indexes that already exist.

Schema version is tracked via a (:SchemaMeta) node so future migrations
can detect which version is live and apply forward-only changes.
"""

from __future__ import annotations

import logging
import time

from app.db.falkor import GraphStore

log = logging.getLogger("app.db.schema")

SCHEMA_VERSION = 1

# ── Range indexes: (Label, property) ─────────────────────────────────────────
_RANGE_INDEXES: list[tuple[str, str]] = [
    # Primary ID indexes (needed for fast MERGE, LOOKUP, and UNIQUE constraints)
    ("Service", "id"),
    ("APIEndpoint", "id"),
    ("Database", "id"),
    ("ThirdParty", "id"),
    ("Library", "id"),
    ("ClientApp", "id"),
    ("Team", "id"),
    ("Simulation", "id"),
    ("SchemaMeta", "id"),

    # Query-critical attribute indexes
    ("Service", "name"),
    ("Service", "tier"),
    ("Service", "status"),
    ("Service", "language"),
    ("APIEndpoint", "path"),
    ("APIEndpoint", "method"),
    ("Database", "type"),
    ("Database", "tier"),
    ("ThirdParty", "name"),
    ("ThirdParty", "category"),
    ("ThirdParty", "tier"),
    ("Library", "name"),
    ("Library", "version"),
    ("ClientApp", "name"),
    ("ClientApp", "platform"),
    ("Team", "name"),
    ("Simulation", "status"),
]

# ── Unique constraints: (Label, property) ────────────────────────────────────
_UNIQUE_CONSTRAINTS: list[tuple[str, str]] = [
    ("Service", "id"),
    ("APIEndpoint", "id"),
    ("Database", "id"),
    ("ThirdParty", "id"),
    ("Library", "id"),
    ("ClientApp", "id"),
    ("Team", "id"),
    ("Simulation", "id"),
    ("SchemaMeta", "id"),
]


def _existing_indexes(store: GraphStore, graph: str | None = None) -> set[tuple[str, str]]:
    """Read current indexes from FalkorDB. Returns a set of (label, field)."""
    existing: set[tuple[str, str]] = set()
    result = store.ro_query("CALL db.indexes()", graph=graph).result_set
    for row in result:
        # FalkorDB returns rows like: [label, [field1, ...], ...]
        if len(row) >= 2:
            label = row[0]
            fields = row[1] if isinstance(row[1], list) else [row[1]]
            status = str(row[7]).upper() if len(row) > 7 else "OPERATIONAL"
            if status == "OPERATIONAL":
                for f in fields:
                    existing.add((str(label), str(f)))
    return existing


def _operational_unique_constraints(store: GraphStore, graph: str | None = None) -> set[tuple[str, str]]:
    """Read successfully enforced node uniqueness constraints from FalkorDB."""
    result = store.ro_query("CALL db.constraints()", graph=graph).result_set
    operational: set[tuple[str, str]] = set()
    for row in result:
        if len(row) < 5:
            continue
        kind, label, properties, entity_type, status = row[:5]
        props = properties if isinstance(properties, list) else [properties]
        if (str(kind).upper() == "UNIQUE" and str(entity_type).upper() == "NODE"
                and str(status).upper() == "OPERATIONAL"):
            operational.update((str(label), str(prop)) for prop in props)
    return operational


def ensure_schema(store: GraphStore, graph: str | None = None) -> int:
    """Create all indexes, constraints, and the SchemaMeta node. Idempotent.

    Call this once during application startup (lifespan) or project ingestion.
    """
    target_graph = graph or store._s.falkordb_graph
    log.info("Ensuring software architecture schema on '%s' (version %d)...", target_graph, SCHEMA_VERSION)

    version_result = store.ro_query(
        "MATCH (m:SchemaMeta {id: 'schema'}) RETURN m.version",
        graph=graph,
    ).result_set
    current_version = version_result[0][0] if version_result else 0
    if current_version and current_version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Graph schema version {current_version} is newer than supported version {SCHEMA_VERSION}."
        )

    existing = _existing_indexes(store, graph=graph)
    created = 0

    # ── Range indexes ────────────────────────────────────────────────────
    for label, prop in _RANGE_INDEXES:
        if not label.isidentifier() or not prop.isidentifier():
            raise ValueError(f"Invalid label or property identifier in index spec: {label}.{prop}")
        if (label, prop) in existing:
            continue
        try:
            store.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})", graph=graph)
            created += 1
        except Exception as exc:
            # "Index already exists" is safe to ignore
            err_str = str(exc).lower()
            if "already indexed" not in err_str and "already exists" not in err_str:
                raise RuntimeError(f"Required index {label}.{prop} could not be created.") from exc

    # ── Unique constraints ───────────────────────────────────────────────
    existing_constraints = _operational_unique_constraints(store, graph=graph)
    for label, prop in _UNIQUE_CONSTRAINTS:
        if not label.isidentifier() or not prop.isidentifier():
            raise ValueError(f"Invalid label or property identifier in constraint spec: {label}.{prop}")
        if (label, prop) in existing_constraints:
            continue
        try:
            store.graph(graph).create_node_unique_constraint(label, prop)
        except Exception as exc:
            err_str = str(exc).lower()
            if "already" not in err_str and "exists" not in err_str:
                raise RuntimeError(f"Required unique constraint {label}.{prop} could not be created.") from exc

    # FalkorDB builds constraints asynchronously. Confirm all are operational
    # before recording the schema version or marking the service ready.
    deadline = time.monotonic() + 15
    required_constraints = set(_UNIQUE_CONSTRAINTS)
    while True:
        operational = _operational_unique_constraints(store, graph=graph)
        if required_constraints.issubset(operational):
            break
        failed = required_constraints - operational
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Unique constraints are not operational: {sorted(failed)}")
        time.sleep(0.25)

    deadline = time.monotonic() + 15
    required_indexes = set(_RANGE_INDEXES)
    while True:
        operational_indexes = _existing_indexes(store, graph=graph)
        missing_indexes = required_indexes - operational_indexes
        if not missing_indexes:
            break
        if time.monotonic() >= deadline:
            missing = ", ".join(f"{label}.{prop}" for label, prop in sorted(missing_indexes))
            raise RuntimeError(f"Required indexes are not operational: {missing}")
        time.sleep(0.25)

    # ── SchemaMeta node ──────────────────────────────────────────────────
    store.query(
        """
        MERGE (m:SchemaMeta {id: 'schema'})
        SET m.version = $version,
            m.domain  = 'software_architecture'
        """,
        {"version": SCHEMA_VERSION},
        graph=graph,
    )

    if not schema_ready(store, graph=graph):
        raise RuntimeError("Schema version marker could not be verified after bootstrap.")

    log.info(
        "Schema bootstrap complete on '%s': %d new indexes checked/created, version=%d",
        target_graph, created, SCHEMA_VERSION,
    )
    return SCHEMA_VERSION


def schema_ready(store: GraphStore, graph: str | None = None) -> bool:
    """Return true only when the supported schema marker and required schema objects are operational."""
    try:
        version_result = store.ro_query(
            "MATCH (m:SchemaMeta {id: 'schema'}) RETURN m.version",
            graph=graph,
        ).result_set
        if not version_result or version_result[0][0] != SCHEMA_VERSION:
            return False
        return (
            set(_RANGE_INDEXES).issubset(_existing_indexes(store, graph=graph))
            and set(_UNIQUE_CONSTRAINTS).issubset(_operational_unique_constraints(store, graph=graph))
        )
    except Exception:
        log.exception("Could not verify graph schema readiness")
        return False
