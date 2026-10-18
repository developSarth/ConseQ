"""Graph fork engine for ConseQ simulations.

The core idea: FalkorDB supports named graphs. To simulate an intervention,
we COPY the live graph into an isolated fork, apply mutations, run cascade
analysis, and then discard the fork. The live graph is never modified.

Flow:
    1. create_fork()   → GRAPH.COPY live → sim_<uuid>
    2. apply_mutation() → DETACH DELETE / SET on the fork
    3. (agent runs cascade queries on the fork)
    4. destroy_fork()  → GRAPH.DELETE sim_<uuid>
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any

from app.core.config import Settings
from app.db.falkor import GraphStore

log = logging.getLogger("app.services.fork")


class ForkManager:
    """Manages temporary graph forks for what-if simulations."""

    def __init__(self, store: GraphStore, settings: Settings) -> None:
        self._store = store
        self._settings = settings
        self._active_forks: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    @property
    def live_graph(self) -> str:
        return self._settings.falkordb_graph

    @property
    def active_forks(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return dict(self._active_forks)

    def create_fork(self, description: str = "", source_graph: str | None = None) -> str:
        """Copy a source graph (defaults to live_graph) into a uniquely named fork. Returns fork ID.

        Raises:
            GraphUnavailableError: if FalkorDB is unreachable
            RuntimeError: if max concurrent forks exceeded
        """
        with self._lock:
            self._sweep_expired()
            if len(self._active_forks) >= self._settings.max_concurrent_forks:
                raise RuntimeError(
                    f"Max concurrent forks ({self._settings.max_concurrent_forks}) reached."
                )

            source = source_graph or self.live_graph
            fork_id = f"sim_{uuid.uuid4().hex}"
            created_at = time.time()
            self._store.graph(source).copy(fork_id)

            self._active_forks[fork_id] = {
                "description": description,
                "created_at": created_at,
                "source_graph": source,
            }
            log.info("Created fork '%s' from '%s'", fork_id, source)
            return fork_id

    def apply_mutation(self, fork_id: str, cypher: str, params: dict[str, Any] | None = None) -> Any:
        """Run a mutation query on a fork graph. Returns the query result.

        The cypher should be a DETACH DELETE, SET, or REMOVE statement.
        This method ONLY runs on fork graphs, never on the live graph.

        Raises:
            ValueError: if fork_id is not tracked or is the live graph name
        """
        self._validate_fork(fork_id)
        log.info("Applying mutation to fork '%s': %s", fork_id, cypher[:120])
        return self._store.query(cypher, params, graph=fork_id)

    def query_fork(self, fork_id: str, cypher: str, params: dict[str, Any] | None = None) -> Any:
        """Run a read-only query on a fork graph. Returns the query result."""
        self._validate_fork(fork_id)
        return self._store.ro_query(cypher, params, graph=fork_id)

    def query_live(self, cypher: str, params: dict[str, Any] | None = None) -> Any:
        """Run a read-only query on the live graph. Returns the query result."""
        return self._store.ro_query(cypher, params)

    def compare(
        self, fork_id: str, cypher: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Run the SAME query on both live and fork, return both result sets.

        This is the core of the delta comparison. The agent uses this to
        show what changed between the live system and the simulation.
        """
        self._validate_fork(fork_id)
        live_result = self._store.ro_query(cypher, params).result_set
        fork_result = self._store.ro_query(cypher, params, graph=fork_id).result_set
        return {
            "live": live_result,
            "fork": fork_result,
            "live_count": len(live_result),
            "fork_count": len(fork_result),
            "delta": len(live_result) - len(fork_result),
        }

    def destroy_fork(self, fork_id: str) -> None:
        """Delete the fork graph and mark the Simulation node as destroyed."""
        with self._lock:
            self._validate_fork(fork_id)
            err: Exception | None = None
            try:
                self._store.graph(fork_id).delete()
            except Exception as exc:
                err = exc
                log.warning("Fork graph '%s' delete failed: %s", fork_id, exc)
            finally:
                # Untrack fork so failed deletions do not permanently exhaust capacity slots
                self._active_forks.pop(fork_id, None)

            if err is not None:
                raise err
            log.info("Destroyed fork '%s'", fork_id)

    def destroy_all(self) -> int:
        """Destroy all active forks. Returns the count destroyed."""
        with self._lock:
            forks = list(self._active_forks.keys())
        destroyed = 0
        for fid in forks:
            try:
                self.destroy_fork(fid)
                destroyed += 1
            except Exception:
                log.exception("Could not clean up fork '%s' during shutdown", fid)
        return destroyed

    def cleanup_orphaned_forks(self) -> int:
        """Scan FalkorDB for any leftover simulation graphs ('sim_*') and delete them."""
        try:
            graphs = self._store.db.list_graphs()
        except Exception as exc:
            log.warning("Could not list graphs to clean orphaned forks: %s", exc)
            return 0

        sim_graphs = [g for g in graphs if isinstance(g, str) and g.startswith("sim_")]
        cleaned = 0
        for g in sim_graphs:
            try:
                self._store.graph(g).delete()
                cleaned += 1
                log.info("Cleaned orphaned fork graph '%s'", g)
            except Exception as exc:
                log.warning("Failed to delete orphaned fork graph '%s': %s", g, exc)

        with self._lock:
            for g in sim_graphs:
                self._active_forks.pop(g, None)

        if cleaned:
            log.info("Cleaned up %d orphaned fork graph(s) on startup", cleaned)
        return cleaned

    # ── internal ─────────────────────────────────────────────────────────

    def _validate_fork(self, fork_id: str) -> None:
        """Guard: the fork must be tracked and must not be the live graph."""
        if fork_id == self.live_graph:
            raise ValueError("Cannot mutate the live graph through the fork engine.")
        if fork_id not in self._active_forks:
            raise ValueError(f"Fork '{fork_id}' is not tracked. Create it first.")

    def _sweep_expired(self) -> None:
        """Destroy forks older than fork_ttl_minutes."""
        ttl_s = self._settings.fork_ttl_minutes * 60
        now = time.time()
        expired = [
            fid for fid, meta in self._active_forks.items()
            if now - meta["created_at"] > ttl_s
        ]
        for fid in expired:
            log.info("Sweeping expired fork '%s'", fid)
            try:
                self.destroy_fork(fid)
            except Exception as exc:
                log.warning("Expired fork '%s' cleanup encountered error: %s", fid, exc)
