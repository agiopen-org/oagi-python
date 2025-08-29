# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import patch

import pytest

from oagi.pyautogui_action_handler import PyautoguiActionHandler
from oagi.types import Action, ActionType


@pytest.fixture
def mock_pyautogui():
    with patch("oagi.pyautogui_action_handler.pyautogui") as mock:
        mock.size.return_value = (1920, 1080)  # Mock screen size
        yield mock


@pytest.fixture
def handler(mock_pyautogui):
    return PyautoguiActionHandler()


def test_click_action(handler, mock_pyautogui):
    action = Action(type=ActionType.CLICK, argument="500, 300", count=1)
    handler([action])

    # Verify denormalized coordinates (500/1000 * 1920, 300/1000 * 1080)
    mock_pyautogui.click.assert_called_once_with(960, 324)


def test_left_double_action(handler, mock_pyautogui):
    action = Action(type=ActionType.LEFT_DOUBLE, argument="400, 250", count=1)
    handler([action])

    # Verify denormalized coordinates
    mock_pyautogui.doubleClick.assert_called_once_with(768, 270)


def test_right_single_action(handler, mock_pyautogui):
    action = Action(type=ActionType.RIGHT_SINGLE, argument="600, 400", count=1)
    handler([action])

    # Verify denormalized coordinates
    mock_pyautogui.rightClick.assert_called_once_with(1152, 432)


def test_drag_action(handler, mock_pyautogui):
    action = Action(type=ActionType.DRAG, argument="100, 100, 500, 300", count=1)
    handler([action])

    # Verify move to start position
    mock_pyautogui.moveTo.assert_any_call(192, 108)
    # Verify drag to end position
    mock_pyautogui.dragTo.assert_called_once_with(960, 324, duration=0.5, button="left")


def test_hotkey_action(handler, mock_pyautogui):
    action = Action(type=ActionType.HOTKEY, argument="ctrl+c", count=1)
    handler([action])

    mock_pyautogui.hotkey.assert_called_once_with("ctrl", "c")


def test_type_action(handler, mock_pyautogui):
    action = Action(type=ActionType.TYPE, argument="Hello World", count=1)
    handler([action])

    mock_pyautogui.typewrite.assert_called_once_with("Hello World")


def test_scroll_action(handler, mock_pyautogui):
    action = Action(type=ActionType.SCROLL, argument="500, 300, up", count=1)
    handler([action])

    # Verify move to position
    mock_pyautogui.moveTo.assert_called_once_with(960, 324)
    # Verify scroll up
    mock_pyautogui.scroll.assert_called_once_with(5)


def test_scroll_down_action(handler, mock_pyautogui):
    action = Action(type=ActionType.SCROLL, argument="500, 300, down", count=1)
    handler([action])

    # Verify scroll down
    mock_pyautogui.scroll.assert_called_once_with(-5)


def test_wait_action(handler, mock_pyautogui):
    with patch("time.sleep") as mock_sleep:
        action = Action(type=ActionType.WAIT, argument="", count=1)
        handler([action])
        mock_sleep.assert_called_once_with(1)


def test_finish_action(handler, mock_pyautogui):
    action = Action(type=ActionType.FINISH, argument="", count=1)
    handler([action])
    # No specific action expected for finish


def test_call_user_action(handler, mock_pyautogui, capsys):
    action = Action(type=ActionType.CALL_USER, argument="", count=1)
    handler([action])

    captured = capsys.readouterr()
    assert "User intervention requested" in captured.out


def test_multiple_count(handler, mock_pyautogui):
    action = Action(type=ActionType.CLICK, argument="500, 300", count=3)
    handler([action])

    assert mock_pyautogui.click.call_count == 3


def test_multiple_actions(handler, mock_pyautogui):
    actions = [
        Action(type=ActionType.CLICK, argument="100, 100", count=1),
        Action(type=ActionType.TYPE, argument="test", count=1),
        Action(type=ActionType.HOTKEY, argument="ctrl+s", count=1),
    ]
    handler(actions)

    mock_pyautogui.click.assert_called_once()
    mock_pyautogui.typewrite.assert_called_once_with("test")
    mock_pyautogui.hotkey.assert_called_once_with("ctrl", "s")


def test_invalid_coordinates_format(handler, mock_pyautogui):
    action = Action(type=ActionType.CLICK, argument="invalid", count=1)

    with pytest.raises(ValueError, match="Invalid coordinates format"):
        handler([action])


def test_type_with_quotes(handler, mock_pyautogui):
    action = Action(type=ActionType.TYPE, argument='"Hello World"', count=1)
    handler([action])

    mock_pyautogui.typewrite.assert_called_once_with("Hello World")
