"""FalkorDB connection manager.

One `GraphStore` per process. It owns a pooled connection, retries on startup,
reconnects lazily, and exposes small, safe query helpers. Every Cypher call in
the project goes through `query()` / `ro_query()` so timeouts, parameterisation
and error mapping are enforced in exactly one place.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from falkordb import FalkorDB
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.core.config import Settings
from app.core.middleware import GraphUnavailableError

log = logging.getLogger("app.db")

_TRANSIENT = (RedisConnectionError, RedisTimeoutError, ConnectionRefusedError, OSError)


class GraphStore:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._db: FalkorDB | None = None

    # ------------------------------------------------------------------ lifecycle
    def connect(self, retries: int | None = None) -> bool:
        """Connect with exponential backoff. Returns True on success, never raises.

        `retries=None` uses the configured startup retries; lazy reconnects pass 0
        so a request fails fast (503) instead of blocking on backoff.
        The API stays up even if the DB is down; readiness reports the problem.
        """
        n = self._s.falkordb_connect_retries if retries is None else retries
        attempts = n + 1
        delay = 0.5
        for i in range(1, attempts + 1):
            try:
                db = FalkorDB(
                    host=self._s.falkordb_host,
                    port=self._s.falkordb_port,
                    username=self._s.falkordb_username,
                    password=(self._s.falkordb_password.get_secret_value()
                              if self._s.falkordb_password else None),
                    ssl=self._s.falkordb_ssl,
                    socket_timeout=self._s.falkordb_socket_timeout_s,
                    socket_connect_timeout=self._s.falkordb_connect_timeout_s,
                    max_connections=self._s.falkordb_max_connections,
                    health_check_interval=30,
                )
                db.connection.ping()
                self._db = db
                log.info("Connected to FalkorDB at %s:%s (graph=%s)",
                         self._s.falkordb_host, self._s.falkordb_port, self._s.falkordb_graph)
                return True
            except _TRANSIENT as exc:
                log.warning("FalkorDB connect attempt %d/%d failed: %s", i, attempts, exc)
                if i < attempts:
                    time.sleep(delay)
                    delay = min(delay * 2, 5.0)
        log.error("FalkorDB unreachable after %d attempts; continuing in degraded mode.", attempts)
        return False

    def close(self) -> None:
        """Release pooled sockets on shutdown."""
        if self._db is not None:
            try:
                self._db.connection.close()
            except RedisError:
                pass
            self._db = None

    # ------------------------------------------------------------------ access
    @property
    def db(self) -> FalkorDB:
        """Return a live client, attempting one lazy reconnect if needed."""
        if self._db is None and not self.connect(retries=0):
            raise GraphUnavailableError(
                f"FalkorDB not reachable at {self._s.falkordb_host}:{self._s.falkordb_port}"
            )
        if self._db is None:
            raise GraphUnavailableError(
                f"FalkorDB not reachable at {self._s.falkordb_host}:{self._s.falkordb_port}"
            )
        return self._db

    def graph(self, name: str | None = None):
        """Select a graph by name (defaults to the configured project graph)."""
        return self.db.select_graph(name or self._s.falkordb_graph)

    # ------------------------------------------------------------------ queries
    def query(self, cypher: str, params: dict[str, Any] | None = None,
              *, graph: str | None = None, timeout_ms: int | None = None):
        """Run a read/write Cypher query. ALWAYS pass user values via `params`."""
        return self._run("query", cypher, params, graph, timeout_ms)

    def ro_query(self, cypher: str, params: dict[str, Any] | None = None,
                 *, graph: str | None = None, timeout_ms: int | None = None):
        """Run a read-only query (server rejects writes; safe for agent tools)."""
        return self._run("ro_query", cypher, params, graph, timeout_ms)

    def _run(self, method: str, cypher: str, params, graph, timeout_ms):
        g = self.graph(graph)
        try:
            return getattr(g, method)(
                cypher, params or {}, timeout=timeout_ms or self._s.falkordb_query_timeout_ms
            )
        except _TRANSIENT as exc:
            # Drop the client so the next call reconnects.
            self._db = None
            raise GraphUnavailableError(f"FalkorDB connection lost: {exc}") from exc

    # ------------------------------------------------------------------ health
    def ping(self) -> dict[str, Any]:
        """Measure round-trip latency and confirm the graph module is loaded."""
        try:
            t0 = time.perf_counter()
            self.db.connection.ping()
            ping_ms = (time.perf_counter() - t0) * 1000
            graphs = self.db.list_graphs()  # GRAPH.LIST -> proves FalkorDB module is active
        except _TRANSIENT as exc:
            self._db = None
            raise GraphUnavailableError(f"FalkorDB ping failed: {exc}") from exc
        return {
            "host": f"{self._s.falkordb_host}:{self._s.falkordb_port}",
            "latency_ms": round(ping_ms, 2),
            "graph": self._s.falkordb_graph,
            "graph_exists": self._s.falkordb_graph in graphs,
            "graphs": graphs,
        }

    def is_healthy(self) -> bool:
        """Cheap boolean check for readiness probes; never raises."""
        try:
            self.ping()
            return True
        except GraphUnavailableError:
            return False
