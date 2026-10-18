"""Shared pytest fixtures for ConseQ."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture(scope="session")
def store(client):
    return client.app.state.graph_store


@pytest.fixture(scope="session")
def fork_manager(client):
    return client.app.state.fork_manager


@pytest.fixture(scope="session")
def falkor_up(store) -> bool:
    return store.is_healthy()
