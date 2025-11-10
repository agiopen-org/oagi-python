import os

import pytest
from fastapi.testclient import TestClient

from oagi.server import ServerConfig, create_app
from oagi.server.session_store import session_store
from oagi.server.socketio_server import (
    _registered_namespaces,
    get_or_create_namespace,
    socket_app,
)


@pytest.fixture
def test_app():
    os.environ["OAGI_API_KEY"] = "test-api-key"

    return create_app()


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


@pytest.mark.parametrize(
    "endpoint,expected_keys",
    [
        ("/health", ["status", "server", "config", "sessions"]),
        ("/", ["status", "name"]),
        ("/sessions", ["total", "sessions"]),
    ],
)
def test_api_endpoints(client, endpoint, expected_keys):
    response = client.get(endpoint)
    assert response.status_code == 200
    data = response.json()
    for key in expected_keys:
        assert key in data


def test_session_not_found(client):
    response = client.get("/sessions/non_existent")
    assert response.status_code == 404

    response = client.delete("/sessions/non_existent")
    assert response.status_code == 404


def test_cleanup_sessions(client):
    response = client.post("/sessions/cleanup?timeout_hours=0.5")
    assert response.status_code == 200
    data = response.json()
    assert "cleaned" in data
    assert "remaining" in data


@pytest.mark.asyncio
async def test_session_management():
    session_store.sessions.clear()

    session_id = session_store.create_session(
        instruction="Test task",
        model="test-model",
    )

    assert session_id.startswith("ses_")
    assert len(session_store.sessions) == 1

    session = session_store.get_session(session_id)
    assert session.instruction == "Test task"


@pytest.mark.asyncio
async def test_namespace_registration():
    os.environ["OAGI_API_KEY"] = "test-key"

    config = ServerConfig()
    namespace = "/session/test_123"

    ns = get_or_create_namespace(namespace, config)
    assert ns.namespace == namespace
    assert namespace in _registered_namespaces

    ns2 = get_or_create_namespace(namespace, config)
    assert ns2 is ns


@pytest.mark.asyncio
async def test_socket_app_exists():
    assert socket_app is not None
    assert callable(socket_app)
