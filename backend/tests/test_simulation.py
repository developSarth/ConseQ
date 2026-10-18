"""Unit and integration tests for ECHO simulation routes and agent logic."""

from app.agent.parser import parse_intent
from app.core.config import get_settings
from app.schemas.simulation import SimulationType


def test_parser_failure_intent():
    settings = get_settings()
    intent = parse_intent("What happens if our authentication service goes offline?", settings)
    assert intent.simulation_type == SimulationType.FAILURE
    assert "auth" in intent.target_name.lower()


def test_parser_upgrade_intent():
    settings = get_settings()
    intent = parse_intent("What if I upgrade this shared library to version 3?", settings)
    assert intent.simulation_type == SimulationType.UPGRADE
    assert intent.target_version is not None
    assert "3" in intent.target_version


def test_parser_recovery_intent():
    settings = get_settings()
    intent = parse_intent("How can we keep checkout working if the payment provider fails?", settings)
    assert intent.simulation_type == SimulationType.RECOVERY


def test_preset_scenarios_endpoint(client):
    r = client.get("/simulate/scenarios")
    assert r.status_code == 200
    scenarios = r.json()
    assert len(scenarios) >= 3
    types = {s["type"] for s in scenarios}
    assert "failure" in types
    assert "upgrade" in types
    assert "recovery" in types


def test_topology_endpoint(client):
    r = client.get("/graph/topology")
    # In degraded mode (DB offline) it returns 503 or 200 with empty nodes
    assert r.status_code in (200, 503)
