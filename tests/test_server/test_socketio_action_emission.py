# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import AsyncMock

import pytest

from oagi.server.config import ServerConfig
from oagi.server.session_store import Session
from oagi.server.socketio_server import SessionNamespace
from oagi.types import Action, ActionType


@pytest.fixture
def namespace(monkeypatch):
    monkeypatch.setenv("OAGI_API_KEY", "test-api-key")
    return SessionNamespace("/session/test_action_emit", ServerConfig())


@pytest.fixture
def session():
    test_session = Session(
        session_id="ses_test_action_emit",
        instruction="test instruction",
    )
    test_session.socket_id = "socket-id"
    return test_session


@pytest.mark.asyncio
async def test_left_click_drag_emits_drag_with_last_cursor(namespace, session):
    session.last_cursor_x = 10
    session.last_cursor_y = 20
    namespace.call = AsyncMock(return_value={"success": True})

    action = Action(type=ActionType.LEFT_CLICK_DRAG, argument="100, 200", count=1)
    await namespace._emit_single_action(session, action, index=0, total=1)

    assert namespace.call.await_count == 1
    event_name = namespace.call.await_args_list[0].args[0]
    payload = namespace.call.await_args_list[0].args[1]

    assert event_name == "drag"
    assert payload["x1"] == 10
    assert payload["y1"] == 20
    assert payload["x2"] == 100
    assert payload["y2"] == 200


@pytest.mark.asyncio
async def test_press_click_emits_press_click_event_with_keys(namespace, session):
    namespace.call = AsyncMock(return_value={"success": True})

    action = Action(
        type=ActionType.PRESS_CLICK,
        argument='{"keys":["ctrl"],"click_type":"left_click","coordinate":[500,300]}',
        count=1,
    )
    await namespace._emit_single_action(session, action, index=0, total=1)

    assert namespace.call.await_count == 1
    event_name = namespace.call.await_args_list[0].args[0]
    payload = namespace.call.await_args_list[0].args[1]

    assert event_name == "press_click"
    assert payload["keys"] == ["ctrl"]
    assert payload["click_type"] == "left_click"
    assert payload["x"] == 500
    assert payload["y"] == 300


@pytest.mark.asyncio
async def test_press_click_falls_back_to_plain_click_on_error(namespace, session):
    namespace.call = AsyncMock(side_effect=[RuntimeError("unsupported"), {"success": True}])

    action = Action(
        type=ActionType.PRESS_CLICK,
        argument='{"keys":["ctrl"],"click_type":"left_click","coordinate":[500,300]}',
        count=1,
    )
    await namespace._emit_single_action(session, action, index=0, total=1)

    assert namespace.call.await_count == 2
    first_event = namespace.call.await_args_list[0].args[0]
    second_event = namespace.call.await_args_list[1].args[0]

    assert first_event == "press_click"
    assert second_event == "click"


@pytest.mark.asyncio
async def test_wait_seconds_converted_to_milliseconds(namespace, session):
    namespace.call = AsyncMock(return_value={"success": True})

    action = Action(type=ActionType.WAIT, argument="2.5", count=1)
    await namespace._emit_single_action(session, action, index=0, total=1)

    assert namespace.call.await_count == 1
    event_name = namespace.call.await_args_list[0].args[0]
    payload = namespace.call.await_args_list[0].args[1]

    assert event_name == "wait"
    assert payload["duration_ms"] == 2500
