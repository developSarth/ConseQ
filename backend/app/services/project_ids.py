"""Validation helpers for server-generated project graph names."""

from __future__ import annotations

import re


# Eight-character IDs were used by the first ingestion implementation. Keep
# accepting those while new projects use the collision-resistant full UUID.
_PROJECT_GRAPH_RE = re.compile(r"^proj_(?:[0-9a-f]{8}|[0-9a-f]{32})$")


def is_project_graph_id(value: str) -> bool:
    """Return whether value has the exact format generated for project graphs."""
    return bool(_PROJECT_GRAPH_RE.fullmatch(value))
