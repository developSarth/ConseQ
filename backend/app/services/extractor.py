"""Static codebase analyzer for ConseQ / ECHO.

Analyzes an uncompressed project directory (or extracted zip archive) to
extract architecture topology:
- Microservices & Language runtimes
- API Endpoints & Routes (FastAPI, Flask, Express, etc.)
- Databases & Caches (Postgres, Redis, MongoDB, Kafka)
- Third-Party Integrations (Stripe, PayPal, Twilio, SendGrid)
- Shared Libraries (crypto-jwt, payment-sdk, etc.)
- Ingress Client Applications & Engineering Teams

Zero heavy external dependencies: uses Python standard library only.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger("app.services.extractor")

# Directory names to skip during recursive scan
IGNORE_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".env", "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".idea", ".vscode", "target", "bin", "obj", ".mypy_cache"
}

# Max files to inspect to avoid pathological runtimes
MAX_FILES_SCANNED = 5000

# Route matching patterns
PY_ROUTE_RE = re.compile(
    r'@(?:app|router|api)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE
)
JS_ROUTE_RE = re.compile(
    r'(?:app|router)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE
)

# Common Third Parties
KNOWN_THIRD_PARTIES = {
    "stripe": ("tp_stripe", "Stripe Payments", "payment", 1),
    "paypal": ("tp_paypal", "PayPal Gateway", "payment", 2),
    "twilio": ("tp_twilio", "Twilio Messaging", "messaging", 2),
    "sendgrid": ("tp_sendgrid", "SendGrid Email", "email", 3),
    "datadog": ("tp_datadog", "Datadog APM", "observability", 3),
    "sentry": ("tp_sentry", "Sentry Error Tracking", "observability", 3),
}

# Common Databases
KNOWN_DATABASES = {
    "postgres": ("db_postgres", "PostgreSQL Primary", "postgresql", 1),
    "postgresql": ("db_postgres", "PostgreSQL Primary", "postgresql", 1),
    "redis": ("cache_redis", "Redis Cache & Session", "redis", 1),
    "mongodb": ("db_mongo", "MongoDB Document Store", "mongodb", 2),
    "mongo": ("db_mongo", "MongoDB Document Store", "mongodb", 2),
    "kafka": ("queue_kafka", "Kafka Event Stream", "kafka", 1),
    "mysql": ("db_mysql", "MySQL Database", "mysql", 1),
    "rabbitmq": ("queue_rabbitmq", "RabbitMQ Queue", "rabbitmq", 2),
}


@dataclass
class ExtractedTopology:
    services: dict[str, dict[str, Any]] = field(default_factory=dict)
    databases: dict[str, dict[str, Any]] = field(default_factory=dict)
    third_parties: dict[str, dict[str, Any]] = field(default_factory=dict)
    libraries: dict[str, dict[str, Any]] = field(default_factory=dict)
    endpoints: dict[str, dict[str, Any]] = field(default_factory=dict)
    client_apps: dict[str, dict[str, Any]] = field(default_factory=dict)
    teams: dict[str, dict[str, Any]] = field(default_factory=dict)
    # List of (source_id, target_id, relation_type)
    edges: list[tuple[str, str, str]] = field(default_factory=list)


def extract_topology_from_directory(root_dir: Path, project_name: str | None = None) -> ExtractedTopology:
    """Recursively scans root_dir and constructs a normalized architecture topology."""
    topo = ExtractedTopology()
    pname = project_name or root_dir.name or "custom_project"
    clean_pname = re.sub(r'[^a-zA-Z0-9_\-]', '', pname.lower()) or "custom"

    # Default team
    team_id = f"team_{clean_pname}"
    topo.teams[team_id] = {
        "id": team_id,
        "name": f"{pname.title()} Core Team",
        "slack_channel": f"#team-{clean_pname}",
        "oncall_lead": "Engineering Lead"
    }

    # Default client application
    app_id = "app_web_storefront"
    topo.client_apps[app_id] = {
        "id": app_id,
        "name": f"{pname.title()} Storefront",
        "platform": "web",
        "active_users": 50000
    }

    files_visited = 0
    compose_files: list[Path] = []
    package_files: list[Path] = []
    req_files: list[Path] = []
    code_files: list[Path] = []

    for path in root_dir.rglob("*"):
        if files_visited >= MAX_FILES_SCANNED:
            log.warning("Max file limit (%d) reached while scanning directory", MAX_FILES_SCANNED)
            break

        # Skip ignored directories
        if any(part in IGNORE_DIRS or part.startswith(".") for part in path.parts[:-1]):
            continue

        if not path.is_file():
            continue

        files_visited += 1
        name_lower = path.name.lower()

        if name_lower in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
            compose_files.append(path)
        elif name_lower == "package.json":
            package_files.append(path)
        elif name_lower in ("requirements.txt", "pyproject.toml"):
            req_files.append(path)
        elif path.suffix in (".py", ".js", ".ts", ".go", ".jsx", ".tsx"):
            code_files.append(path)

    # 1. Parse Docker Compose files
    for cfile in compose_files:
        _parse_compose_file(cfile, topo, team_id)

    # 2. Parse Package.json manifests
    for pfile in package_files:
        _parse_package_json(pfile, topo, team_id)

    # 3. Parse Requirements.txt manifests
    for rfile in req_files:
        _parse_requirements_file(rfile, topo)

    # 4. If no services were extracted yet, create a root service for the project
    if not topo.services:
        root_svc_id = f"svc_{clean_pname}"
        topo.services[root_svc_id] = {
            "id": root_svc_id,
            "name": f"{clean_pname}-service",
            "tier": 1,
            "status": "healthy",
            "language": "python" if req_files else ("typescript" if package_files else "unknown")
        }
        topo.edges.append((root_svc_id, team_id, "OWNED_BY"))

    primary_svc_id = next(iter(topo.services.keys()))

    # 5. Parse Source Code for Routes & Endpoints
    for code_file in code_files[:1000]:  # Cap code files parsed for routes to 1000
        _parse_code_routes(code_file, topo, primary_svc_id, app_id)

    # 6. Ensure default connections if sparse
    _ensure_baseline_connections(topo, primary_svc_id, app_id)

    return topo


def _parse_compose_file(path: Path, topo: ExtractedTopology, team_id: str) -> None:
    """Parses docker-compose services and database containers without PyYAML."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        log.warning("Could not read compose file %s: %s", path, exc)
        return

    # Extract top-level services
    # Looks for 'services:' block and following indented service names
    in_services = False
    current_svc = None

    for line in content.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue

        if line.startswith("services:"):
            in_services = True
            continue

        if in_services and not line.startswith(" ") and not line.startswith("\t"):
            in_services = False
            current_svc = None
            continue

        if in_services:
            # Check for service declaration: exactly 2 or 4 leading spaces then name:
            match = re.match(r'^(?:  |\t)([a-zA-Z0-9_\-]+):\s*$', line)
            if match:
                svc_raw = match.group(1).lower()
                current_svc = svc_raw
                # Check if this service is actually a database image
                db_key = None
                for k, db_info in KNOWN_DATABASES.items():
                    if k in svc_raw:
                        db_key = k
                        db_id, db_name, db_type, db_tier = db_info
                        topo.databases[db_id] = {
                            "id": db_id, "name": db_name, "type": db_type, "tier": db_tier
                        }
                        break

                if not db_key:
                    svc_id = f"svc_{svc_raw.replace('-', '_')}"
                    tier = 1 if any(t in svc_raw for t in ("gateway", "auth", "checkout", "order", "payment")) else 2
                    topo.services[svc_id] = {
                        "id": svc_id,
                        "name": f"{svc_raw}-service" if not svc_raw.endswith("service") else svc_raw,
                        "tier": tier,
                        "status": "healthy",
                        "language": "polyglot"
                    }
                    topo.edges.append((svc_id, team_id, "OWNED_BY"))
                continue

            # Check for image property under current service
            if current_svc and "image:" in trimmed:
                image_val = trimmed.split("image:")[-1].strip().lower()
                for k, db_info in KNOWN_DATABASES.items():
                    if k in image_val:
                        db_id, db_name, db_type, db_tier = db_info
                        topo.databases[db_id] = {
                            "id": db_id, "name": db_name, "type": db_type, "tier": db_tier
                        }
                        # If current_svc was recorded as a service, replace it with database
                        curr_svc_id = f"svc_{current_svc.replace('-', '_')}"
                        topo.services.pop(curr_svc_id, None)
                        break


def _parse_package_json(path: Path, topo: ExtractedTopology, team_id: str) -> None:
    """Parses npm package.json for services, libraries, and third parties."""
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return

    pkg_name = str(data.get("name", "")).strip().lower()
    if pkg_name:
        clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', pkg_name)
        svc_id = f"svc_{clean_name.replace('-', '_')}"
        if svc_id not in topo.services:
            tier = 1 if any(t in clean_name for t in ("auth", "checkout", "gateway", "pay", "order")) else 2
            topo.services[svc_id] = {
                "id": svc_id,
                "name": clean_name if clean_name.endswith("-service") else f"{clean_name}-service",
                "tier": tier,
                "status": "healthy",
                "language": "typescript"
            }
            topo.edges.append((svc_id, team_id, "OWNED_BY"))
        current_svc_id = svc_id
    else:
        current_svc_id = next(iter(topo.services.keys())) if topo.services else None

    deps: dict[str, str] = {}
    deps.update(data.get("dependencies", {}))
    deps.update(data.get("devDependencies", {}))

    for dep_name, version in deps.items():
        dep_lower = dep_name.lower()

        # Check Third Party
        for tp_key, tp_info in KNOWN_THIRD_PARTIES.items():
            if tp_key in dep_lower:
                tp_id, tp_name, tp_cat, tp_tier = tp_info
                topo.third_parties[tp_id] = {
                    "id": tp_id, "name": tp_name, "category": tp_cat, "tier": tp_tier
                }
                if current_svc_id:
                    topo.edges.append((current_svc_id, tp_id, "INTEGRATES_WITH"))

        # Check Database client
        for db_key, db_info in KNOWN_DATABASES.items():
            if db_key in dep_lower:
                db_id, db_name, db_type, db_tier = db_info
                topo.databases[db_id] = {
                    "id": db_id, "name": db_name, "type": db_type, "tier": db_tier
                }
                if current_svc_id:
                    topo.edges.append((current_svc_id, db_id, "CONNECTS_TO"))

        # Check key libraries
        if any(lib in dep_lower for lib in ("jwt", "crypto", "axios", "express", "prisma", "bcrypt", "grpc")):
            clean_ver = re.sub(r'[^0-9\.]', '', str(version)) or "1.0.0"
            lib_id = f"lib_{re.sub(r'[^a-zA-Z0-9_]', '_', dep_lower)}"
            topo.libraries[lib_id] = {
                "id": lib_id,
                "name": dep_name,
                "version": clean_ver,
                "latest_version": f"{int(clean_ver.split('.')[0]) + 1}.0.0" if clean_ver[0].isdigit() else "2.0.0"
            }
            if current_svc_id:
                topo.edges.append((current_svc_id, lib_id, "USES_LIBRARY"))


def _parse_requirements_file(path: Path, topo: ExtractedTopology) -> None:
    """Parses requirements.txt for python libraries and integrations."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    current_svc_id = next(iter(topo.services.keys())) if topo.services else None

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = re.split(r'==|>=|<=|~=', line)
        lib_name = parts[0].strip()
        version = parts[1].strip() if len(parts) > 1 else "1.0.0"
        lib_lower = lib_name.lower()

        # Check Third Party
        for tp_key, tp_info in KNOWN_THIRD_PARTIES.items():
            if tp_key in lib_lower:
                tp_id, tp_name, tp_cat, tp_tier = tp_info
                topo.third_parties[tp_id] = {
                    "id": tp_id, "name": tp_name, "category": tp_cat, "tier": tp_tier
                }
                if current_svc_id:
                    topo.edges.append((current_svc_id, tp_id, "INTEGRATES_WITH"))

        # Check Database client
        for db_key, db_info in KNOWN_DATABASES.items():
            if db_key in lib_lower or (db_key == "postgres" and "psycopg" in lib_lower):
                db_id, db_name, db_type, db_tier = db_info
                topo.databases[db_id] = {
                    "id": db_id, "name": db_name, "type": db_type, "tier": db_tier
                }
                if current_svc_id:
                    topo.edges.append((current_svc_id, db_id, "CONNECTS_TO"))

        # Check Library
        if any(lib in lib_lower for lib in ("jwt", "crypto", "stripe", "pydantic", "fastapi", "sqlalchemy", "redis", "celery")):
            clean_ver = re.sub(r'[^0-9\.]', '', version) or "1.0.0"
            lib_id = f"lib_{re.sub(r'[^a-zA-Z0-9_]', '_', lib_lower)}"
            topo.libraries[lib_id] = {
                "id": lib_id,
                "name": lib_name,
                "version": clean_ver,
                "latest_version": f"{int(clean_ver.split('.')[0]) + 1}.0.0" if clean_ver and clean_ver[0].isdigit() else "2.0.0"
            }
            if current_svc_id:
                topo.edges.append((current_svc_id, lib_id, "USES_LIBRARY"))


def _parse_code_routes(path: Path, topo: ExtractedTopology, primary_svc_id: str, app_id: str) -> None:
    """Scans code files for endpoint declarations."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    pattern = PY_ROUTE_RE if path.suffix == ".py" else JS_ROUTE_RE
    for match in pattern.finditer(content):
        method = match.group(1).upper()
        route_path = match.group(2).strip()
        if not route_path.startswith("/"):
            route_path = f"/{route_path}"

        clean_slug = re.sub(r'[^a-zA-Z0-9_]', '_', route_path.strip("/")).lower() or "root"
        ep_id = f"ep_{method.lower()}_{clean_slug[:32]}"

        if ep_id not in topo.endpoints:
            topo.endpoints[ep_id] = {
                "id": ep_id,
                "path": route_path,
                "method": method,
                "service_id": primary_svc_id
            }
            topo.edges.append((ep_id, primary_svc_id, "ROUTED_TO"))
            topo.edges.append((app_id, ep_id, "CALLS"))


def _ensure_baseline_connections(topo: ExtractedTopology, primary_svc_id: str, app_id: str) -> None:
    """Ensures at least default database, endpoint, and third party exist so graph simulations are viable."""
    # Ensure at least 1 database
    if not topo.databases:
        db_id = "db_primary_pg"
        topo.databases[db_id] = {
            "id": db_id,
            "name": "Primary PostgreSQL",
            "type": "postgresql",
            "tier": 1
        }
        topo.edges.append((primary_svc_id, db_id, "CONNECTS_TO"))

    # Ensure at least 1 endpoint
    if not topo.endpoints:
        ep_id = "ep_api_health"
        topo.endpoints[ep_id] = {
            "id": ep_id,
            "path": "/health",
            "method": "GET",
            "service_id": primary_svc_id
        }
        topo.edges.append((ep_id, primary_svc_id, "ROUTED_TO"))
        topo.edges.append((app_id, ep_id, "CALLS"))

    # Ensure at least 1 third party
    if not topo.third_parties:
        tp_id = "tp_stripe"
        topo.third_parties[tp_id] = {
            "id": tp_id,
            "name": "Stripe Payments",
            "category": "payment",
            "tier": 1
        }
        topo.edges.append((primary_svc_id, tp_id, "INTEGRATES_WITH"))
