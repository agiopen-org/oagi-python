import time
from datetime import datetime

import pytest

from oagi.server.session_store import Session, SessionStore


@pytest.fixture
def store():
    return SessionStore()


@pytest.fixture
def session():
    return Session(
        session_id="test_session",
        instruction="Test task",
        mode="actor",
        model="lux-v1",
        temperature=0.5,
    )


def test_session_creation(session):
    assert session.session_id == "test_session"
    assert session.instruction == "Test task"
    assert session.mode == "actor"
    assert session.model == "lux-v1"
    assert session.temperature == 0.5
    assert session.status == "initialized"
    assert len(session.task_id) == 32


def test_create_session(store):
    session_id = store.create_session(
        instruction="Test task",
        mode="planner",
        model="test-model",
        temperature=0.7,
    )

    assert session_id.startswith("ses_")
    session = store.get_session(session_id)
    assert session.instruction == "Test task"
    assert session.mode == "planner"
    assert session.model == "test-model"


def test_create_session_with_custom_id(store):
    custom_id = store.create_session(
        instruction="Custom task",
        session_id="custom_123",
    )

    assert custom_id == "custom_123"
    assert store.get_session(custom_id) is not None


def test_create_session_with_defaults(store):
    session_id = store.create_session(instruction="Test with defaults")
    session = store.get_session(session_id)

    assert session.mode == "actor"  # Default mode
    assert session.model == "lux-v1"  # Default model
    assert session.temperature == 0.0  # Default temperature


def test_get_session_by_socket_id(store):
    session_id = store.create_session("Test task")
    session = store.get_session(session_id)
    session.socket_id = "socket_123"

    found = store.get_session_by_socket_id("socket_123")
    assert found.session_id == session_id

    assert store.get_session_by_socket_id("non_existent") is None


def test_delete_session(store):
    session_id = store.create_session("Test task")

    assert store.delete_session(session_id) is True
    assert store.get_session(session_id) is None
    assert store.delete_session(session_id) is False


def test_update_activity(store):
    session_id = store.create_session("Test task")
    session = store.get_session(session_id)
    original_time = session.last_activity

    time.sleep(0.01)
    store.update_activity(session_id)

    assert store.get_session(session_id).last_activity > original_time


def test_list_sessions(store):
    assert len(store.list_sessions()) == 0

    id1 = store.create_session("Task 1")
    id2 = store.create_session("Task 2")

    sessions = store.list_sessions()
    assert len(sessions) == 2

    session_ids = {s["session_id"] for s in sessions}
    assert {id1, id2} == session_ids


def test_cleanup_inactive_sessions(store):
    active_id = store.create_session("Active")
    inactive_id = store.create_session("Inactive")

    inactive_session = store.get_session(inactive_id)
    inactive_session.last_activity = datetime.now().timestamp() - 3600

    cleaned = store.cleanup_inactive_sessions(1800)
    assert cleaned == 1
    assert store.get_session(active_id) is not None
    assert store.get_session(inactive_id) is None


@pytest.mark.parametrize("status", ["initialized", "running", "completed", "failed"])
def test_session_status_transitions(session, status):
    session.status = status
    assert session.status == status
