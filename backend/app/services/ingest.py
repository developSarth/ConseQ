"""Ingestion service for analyzing and loading user codebases into FalkorDB graphs."""

from __future__ import annotations

import io
import logging
import re
import shutil
import stat
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath

from app.db.falkor import GraphStore
from app.db.schema import ensure_schema
from app.core.config import REPO_ROOT
from app.core.middleware import GraphUnavailableError
from app.schemas.project import IngestResponse
from app.services.extractor import ExtractedTopology, extract_topology_from_directory

log = logging.getLogger("app.services.ingest")

# Constraints for safe zip extraction
MAX_ARCHIVE_SIZE_BYTES = 50 * 1024 * 1024       # 50 MB
MAX_UNCOMPRESSED_SIZE_BYTES = 150 * 1024 * 1024  # 150 MB
MAX_ARCHIVE_FILE_COUNT = 5000
MAX_COMPRESSION_RATIO = 1000


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

                # 2. Validate and extract safely. Reject Windows-style path
                # components on every platform to avoid cross-platform Zip-Slip.
                for member in infolist:
                    raw_name = member.filename
                    posix_name = PurePosixPath(raw_name)
                    windows_name = PureWindowsPath(raw_name)
                    if (not raw_name or "\\" in raw_name or "\x00" in raw_name
                            or posix_name.is_absolute() or windows_name.is_absolute()
                            or windows_name.drive
                            or ".." in posix_name.parts
                            or stat.S_ISLNK(member.external_attr >> 16)):
                        raise SecurityValidationError(
                            f"Illegal path traversal detected in archive: '{member.filename}'"
                        )
                    if member.file_size and (
                        member.compress_size == 0
                        or member.file_size / member.compress_size > MAX_COMPRESSION_RATIO
                    ):
                        raise SecurityValidationError(
                            f"Archive member has an unsafe compression ratio: '{member.filename}'"
                        )
                    target_path = (tmp_dir / Path(*posix_name.parts)).resolve()
                    if not target_path.is_relative_to(tmp_dir.resolve()):
                        raise SecurityValidationError(
                            f"Illegal path traversal detected in archive: '{member.filename}'"
                        )
                    if member.is_dir():
                        target_path.mkdir(parents=True, exist_ok=True)
                        continue
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as source, target_path.open("wb") as target:
                        shutil.copyfileobj(source, target, length=1024 * 1024)

        except zipfile.BadZipFile as exc:
            raise IngestionError("Uploaded file is not a valid or readable ZIP archive.") from exc
        except (RuntimeError, NotImplementedError) as exc:
            raise IngestionError("Uploaded ZIP uses unsupported compression or encryption.") from exc

        # 3. Analyze codebase
        topo = extract_topology_from_directory(tmp_dir, project_name=clean_proj_name)

    # 4. Populate dedicated project graph in FalkorDB
    project_id = f"proj_{uuid.uuid4().hex}"
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
    if not dir_path.is_relative_to(REPO_ROOT.resolve()):
        raise SecurityValidationError("Directory ingestion is restricted to the application workspace.")

    clean_proj_name = project_name or dir_path.name or "Local Project"
    topo = extract_topology_from_directory(dir_path, project_name=clean_proj_name)

    project_id = f"proj_{uuid.uuid4().hex}"
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

    try:
        ensure_schema(store, graph=graph_name)

        node_groups = (
            ("Team", list(topo.teams.values())),
            ("ClientApp", list(topo.client_apps.values())),
            ("Service", list(topo.services.values())),
            ("Database", list(topo.databases.values())),
            ("ThirdParty", list(topo.third_parties.values())),
            ("Library", list(topo.libraries.values())),
            ("APIEndpoint", list(topo.endpoints.values())),
        )
        for label, rows in node_groups:
            if rows:
                store.query(
                    f"UNWIND $rows AS row MERGE (n:{label} {{id: row.id}}) SET n += row",
                    {"rows": rows},
                    graph=graph_name,
                )

        allowed_relationships = {
            "CALLS", "ROUTED_TO", "CONNECTS_TO", "INTEGRATES_WITH", "USES_LIBRARY", "OWNED_BY"
        }
        by_relationship: dict[str, list[dict[str, str]]] = {}
        for src, tgt, rel in topo.edges:
            if rel in allowed_relationships:
                by_relationship.setdefault(rel, []).append({"src": src, "tgt": tgt})
        for rel, rows in by_relationship.items():
            store.query(
                f"""UNWIND $rows AS row
                    MATCH (a {{id: row.src}}), (b {{id: row.tgt}})
                    MERGE (a)-[r:{rel}]->(b)""",
                {"rows": rows},
                graph=graph_name,
            )
    except GraphUnavailableError:
        try:
            store.graph(graph_name).delete()
        except Exception:
            log.exception("Could not remove incomplete project graph '%s' after DB loss", graph_name)
        raise
    except Exception as exc:
        # Never leave a half-ingested graph that callers may mistake for ready.
        try:
            store.graph(graph_name).delete()
        except Exception:
            log.exception("Could not remove incomplete project graph '%s'", graph_name)
        raise IngestionError("Could not initialize or populate the project graph.") from exc

    log.info("Populated project graph '%s' successfully.", graph_name)
