"""Ingestion service for analyzing and loading user codebases into FalkorDB graphs."""

from __future__ import annotations

import io
import logging
import re
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any

from app.db.falkor import GraphStore
from app.db.schema import ensure_schema
from app.schemas.project import IngestResponse
from app.services.extractor import ExtractedTopology, extract_topology_from_directory

log = logging.getLogger("app.services.ingest")

# Constraints for safe zip extraction
MAX_ARCHIVE_SIZE_BYTES = 50 * 1024 * 1024       # 50 MB
MAX_UNCOMPRESSED_SIZE_BYTES = 150 * 1024 * 1024  # 150 MB
MAX_ARCHIVE_FILE_COUNT = 5000


class IngestionError(Exception):
    """Base exception for archive or directory ingestion failures."""


class SecurityValidationError(IngestionError):
    """Raised when an uploaded archive violates security boundaries (Zip-Slip, bomb)."""


def ingest_zip_archive(
    zip_bytes: bytes,
    filename: str,
    store: GraphStore,
    project_name: str | None = None,
) -> IngestResponse:
    """Safely unpacks a zip archive into an isolated sandbox and builds a FalkorDB project graph."""
    start_time = time.monotonic()

    if len(zip_bytes) > MAX_ARCHIVE_SIZE_BYTES:
        raise SecurityValidationError(
            f"Uploaded archive exceeds maximum allowed size of {MAX_ARCHIVE_SIZE_BYTES // (1024*1024)}MB."
        )

    clean_proj_name = project_name or Path(filename).stem
    clean_proj_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', clean_proj_name).strip() or "Custom Storefront"

    with tempfile.TemporaryDirectory(prefix="conseq_ingest_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                # 1. Inspect archive entries for Zip-Slip & bomb attacks
                infolist = zf.infolist()
                if len(infolist) > MAX_ARCHIVE_FILE_COUNT:
                    raise SecurityValidationError(
                        f"Archive contains {len(infolist)} files, exceeding limit of {MAX_ARCHIVE_FILE_COUNT}."
                    )

                total_uncompressed = sum(info.file_size for info in infolist)
                if total_uncompressed > MAX_UNCOMPRESSED_SIZE_BYTES:
                    raise SecurityValidationError(
                        f"Uncompressed archive size ({total_uncompressed // (1024*1024)}MB) exceeds limit."
                    )

                # 2. Extract safely
                for member in infolist:
                    target_path = (tmp_dir / member.filename).resolve()
                    if not target_path.is_relative_to(tmp_dir.resolve()):
                        raise SecurityValidationError(
                            f"Illegal path traversal detected in archive: '{member.filename}'"
                        )
                    zf.extract(member, tmp_dir)

        except zipfile.BadZipFile as exc:
            raise IngestionError("Uploaded file is not a valid or readable ZIP archive.") from exc

        # 3. Analyze codebase
        topo = extract_topology_from_directory(tmp_dir, project_name=clean_proj_name)

    # 4. Populate dedicated project graph in FalkorDB
    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    _populate_project_graph(topo, project_id, store)

    elapsed_ms = (time.monotonic() - start_time) * 1000.0

    return IngestResponse(
        project_id=project_id,
        project_name=clean_proj_name,
        node_count=(
            len(topo.services) + len(topo.databases) + len(topo.third_parties) +
            len(topo.libraries) + len(topo.endpoints) + len(topo.client_apps) + len(topo.teams)
        ),
        edge_count=len(topo.edges),
        services_count=len(topo.services),
        databases_count=len(topo.databases),
        endpoints_count=len(topo.endpoints),
        third_parties_count=len(topo.third_parties),
        libraries_count=len(topo.libraries),
        services=[s["name"] for s in topo.services.values()],
        databases=[d["name"] for d in topo.databases.values()],
        endpoints=[f"{ep['method']} {ep['path']}" for ep in topo.endpoints.values()],
        libraries=[l["name"] for l in topo.libraries.values()],
        execution_time_ms=round(elapsed_ms, 2),
        message=f"Codebase '{clean_proj_name}' analyzed successfully into isolated graph '{project_id}'."
    )


def ingest_local_directory(
    directory_path: str,
    store: GraphStore,
    project_name: str | None = None,
) -> IngestResponse:
    """Analyzes a local filesystem directory and loads it into a FalkorDB project graph."""
    start_time = time.monotonic()
    dir_path = Path(directory_path).resolve()

    if not dir_path.exists() or not dir_path.is_dir():
        raise IngestionError(f"Directory '{directory_path}' does not exist or is not a directory.")

    clean_proj_name = project_name or dir_path.name or "Local Project"
    topo = extract_topology_from_directory(dir_path, project_name=clean_proj_name)

    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    _populate_project_graph(topo, project_id, store)

    elapsed_ms = (time.monotonic() - start_time) * 1000.0

    return IngestResponse(
        project_id=project_id,
        project_name=clean_proj_name,
        node_count=(
            len(topo.services) + len(topo.databases) + len(topo.third_parties) +
            len(topo.libraries) + len(topo.endpoints) + len(topo.client_apps) + len(topo.teams)
        ),
        edge_count=len(topo.edges),
        services_count=len(topo.services),
        databases_count=len(topo.databases),
        endpoints_count=len(topo.endpoints),
        third_parties_count=len(topo.third_parties),
        libraries_count=len(topo.libraries),
        services=[s["name"] for s in topo.services.values()],
        databases=[d["name"] for d in topo.databases.values()],
        endpoints=[f"{ep['method']} {ep['path']}" for ep in topo.endpoints.values()],
        libraries=[l["name"] for l in topo.libraries.values()],
        execution_time_ms=round(elapsed_ms, 2),
        message=f"Directory '{clean_proj_name}' analyzed successfully into isolated graph '{project_id}'."
    )


def _populate_project_graph(topo: ExtractedTopology, graph_name: str, store: GraphStore) -> None:
    """Initializes schema and merges all extracted nodes and relationships into FalkorDB."""
    log.info("Populating extracted project topology into '%s'...", graph_name)

    # 1. Ensure indexes & constraints on the new graph
    try:
        ensure_schema(store, graph=graph_name)
    except Exception as exc:
        log.warning("Schema setup on '%s' had warning (%s); proceeding with MERGE", graph_name, exc)

    # 2. Merge Teams
    for t in topo.teams.values():
        store.query(
            """MERGE (tm:Team {id: $id})
               SET tm.name = $name, tm.slack_channel = $slack, tm.oncall_lead = $lead""",
            {"id": t["id"], "name": t["name"], "slack": t.get("slack_channel", ""), "lead": t.get("oncall_lead", "")},
            graph=graph_name,
        )

    # 3. Merge Client Apps
    for c in topo.client_apps.values():
        store.query(
            """MERGE (ca:ClientApp {id: $id})
               SET ca.name = $name, ca.platform = $platform, ca.active_users = $users""",
            {"id": c["id"], "name": c["name"], "platform": c.get("platform", "web"), "users": c.get("active_users", 10000)},
            graph=graph_name,
        )

    # 4. Merge Services
    for s in topo.services.values():
        store.query(
            """MERGE (svc:Service {id: $id})
               SET svc.name = $name, svc.tier = $tier, svc.status = $status, svc.language = $lang""",
            {"id": s["id"], "name": s["name"], "tier": s.get("tier", 1), "status": s.get("status", "healthy"), "lang": s.get("language", "polyglot")},
            graph=graph_name,
        )

    # 5. Merge Databases
    for d in topo.databases.values():
        store.query(
            """MERGE (db:Database {id: $id})
               SET db.name = $name, db.type = $type, db.tier = $tier""",
            {"id": d["id"], "name": d["name"], "type": d.get("type", "postgresql"), "tier": d.get("tier", 1)},
            graph=graph_name,
        )

    # 6. Merge Third Parties
    for tp in topo.third_parties.values():
        store.query(
            """MERGE (t:ThirdParty {id: $id})
               SET t.name = $name, t.category = $cat, t.tier = $tier""",
            {"id": tp["id"], "name": tp["name"], "cat": tp.get("category", "payment"), "tier": tp.get("tier", 1)},
            graph=graph_name,
        )

    # 7. Merge Libraries
    for lib in topo.libraries.values():
        store.query(
            """MERGE (l:Library {id: $id})
               SET l.name = $name, l.version = $ver, l.latest_version = $latest""",
            {"id": lib["id"], "name": lib["name"], "ver": lib.get("version", "1.0.0"), "latest": lib.get("latest_version", "2.0.0")},
            graph=graph_name,
        )

    # 8. Merge Endpoints
    for ep in topo.endpoints.values():
        store.query(
            """MERGE (e:APIEndpoint {id: $id})
               SET e.path = $path, e.method = $method""",
            {"id": ep["id"], "path": ep["path"], "method": ep["method"]},
            graph=graph_name,
        )

    # 9. Merge Relationships
    for src, tgt, rel in topo.edges:
        if rel in ("CALLS", "ROUTED_TO", "CONNECTS_TO", "INTEGRATES_WITH", "USES_LIBRARY", "OWNED_BY"):
            store.query(
                f"""MATCH (a {{id: $src}}), (b {{id: $tgt}})
                   MERGE (a)-[r:{rel}]->(b)""",
                {"src": src, "tgt": tgt},
                graph=graph_name,
            )

    log.info("Populated project graph '%s' successfully.", graph_name)
