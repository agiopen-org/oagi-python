# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import patch

import pytest

from oagi.pyautogui_action_handler import PyautoguiActionHandler, PyautoguiConfig
from oagi.types import Action, ActionType


@pytest.fixture
def mock_pyautogui():
    with patch("oagi.pyautogui_action_handler.pyautogui") as mock:
        mock.size.return_value = (1920, 1080)
        yield mock


@pytest.fixture
def config():
    return PyautoguiConfig()


@pytest.fixture
def handler(mock_pyautogui):
    return PyautoguiActionHandler()


@pytest.mark.parametrize(
    "action_type,argument,expected_method,expected_coords",
    [
        (ActionType.CLICK, "500, 300", "click", (960, 324)),
        (ActionType.LEFT_DOUBLE, "400, 250", "doubleClick", (768, 270)),
        (ActionType.LEFT_TRIPLE, "350, 200", "tripleClick", (672, 216)),
        (ActionType.RIGHT_SINGLE, "600, 400", "rightClick", (1152, 432)),
    ],
)
def test_coordinate_based_actions(
    handler, mock_pyautogui, action_type, argument, expected_method, expected_coords
):
    action = Action(type=action_type, argument=argument, count=1)
    handler([action])

    getattr(mock_pyautogui, expected_method).assert_called_once_with(*expected_coords)


def test_drag_action(handler, mock_pyautogui, config):
    action = Action(type=ActionType.DRAG, argument="100, 100, 500, 300", count=1)
    handler([action])

    mock_pyautogui.moveTo.assert_any_call(192, 108)
    mock_pyautogui.dragTo.assert_called_once_with(
        960, 324, duration=config.drag_duration, button="left"
    )


@pytest.mark.parametrize(
    "action_type,argument,expected_method,expected_args",
    [
        (ActionType.HOTKEY, "ctrl+c", "hotkey", ("ctrl", "c")),
        (ActionType.TYPE, "Hello World", "typewrite", ("Hello World",)),
    ],
)
def test_text_based_actions(
    handler, mock_pyautogui, action_type, argument, expected_method, expected_args
):
    action = Action(type=action_type, argument=argument, count=1)
    handler([action])

    getattr(mock_pyautogui, expected_method).assert_called_once_with(*expected_args)


@pytest.mark.parametrize(
    "direction,expected_amount_multiplier",
    [("up", 1), ("down", -1)],
)
def test_scroll_actions(
    handler, mock_pyautogui, config, direction, expected_amount_multiplier
):
    action = Action(type=ActionType.SCROLL, argument=f"500, 300, {direction}", count=1)
    handler([action])

    mock_pyautogui.moveTo.assert_called_once_with(960, 324)
    expected_scroll_amount = config.scroll_amount * expected_amount_multiplier
    mock_pyautogui.scroll.assert_called_once_with(expected_scroll_amount)


def test_wait_action(handler, mock_pyautogui, config):
    with patch("time.sleep") as mock_sleep:
        action = Action(type=ActionType.WAIT, argument="", count=1)
        handler([action])
        mock_sleep.assert_called_once_with(config.wait_duration)


def test_finish_action(handler, mock_pyautogui):
    action = Action(type=ActionType.FINISH, argument="", count=1)
    handler([action])


def test_call_user_action(handler, mock_pyautogui, capsys):
    action = Action(type=ActionType.CALL_USER, argument="", count=1)
    handler([action])

    captured = capsys.readouterr()
    assert "User intervention requested" in captured.out


class TestActionExecution:
    def test_multiple_count(self, handler, mock_pyautogui):
        action = Action(type=ActionType.CLICK, argument="500, 300", count=3)
        handler([action])

        assert mock_pyautogui.click.call_count == 3

    def test_multiple_actions(self, handler, mock_pyautogui):
        actions = [
            Action(type=ActionType.CLICK, argument="100, 100", count=1),
            Action(type=ActionType.TYPE, argument="test", count=1),
            Action(type=ActionType.HOTKEY, argument="ctrl+s", count=1),
        ]
        handler(actions)

        mock_pyautogui.click.assert_called_once()
        mock_pyautogui.typewrite.assert_called_once_with("test")
        mock_pyautogui.hotkey.assert_called_once_with("ctrl", "s")


class TestInputValidation:
    def test_invalid_coordinates_format(self, handler, mock_pyautogui):
        action = Action(type=ActionType.CLICK, argument="invalid", count=1)

        with pytest.raises(ValueError, match="Invalid coordinates format"):
            handler([action])

    def test_type_with_quotes(self, handler, mock_pyautogui):
        action = Action(type=ActionType.TYPE, argument='"Hello World"', count=1)
        handler([action])

        mock_pyautogui.typewrite.assert_called_once_with("Hello World")
