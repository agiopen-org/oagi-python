# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import sys
from unittest.mock import MagicMock, patch

import pytest

if sys.platform != "darwin":
    pytest.skip(
        "Skipping macOS-specific tests on non-macOS platform", allow_module_level=True
    )

from oagi.handler import _macos  # noqa: E402
from oagi.handler.pyautogui_action_handler import PyautoguiActionHandler
from oagi.types import Action, ActionType


@pytest.fixture
def mock_pyautogui():
    with patch("oagi.handler.pyautogui_action_handler.pyautogui") as mock:
        mock.size.return_value = (1920, 1080)
        yield mock


@pytest.fixture
def mock_quartz():
    mock = MagicMock()
    # Set up constants
    mock.kCGEventLeftMouseDown = 1
    mock.kCGEventLeftMouseUp = 2
    mock.kCGMouseButtonLeft = 0
    mock.kCGMouseEventClickState = 99
    mock.kCGHIDEventTap = 55
    return mock


def test_macos_click_implementation(mock_quartz):
    """Test the low-level macos_click function."""
    with (
        patch.object(_macos, "Quartz", mock_quartz),
        patch("oagi.handler._macos.pyautogui") as mock_pg,
    ):
        # Test triple click
        _macos.macos_click(100, 200, clicks=3)

        # Should move mouse
        mock_pg.moveTo.assert_called_once_with(100, 200)

        # Should create 6 events (3 clicks * 2 events/click)
        assert mock_quartz.CGEventCreateMouseEvent.call_count == 6

        # Should post 6 events
        assert mock_quartz.CGEventPost.call_count == 6

        # Verify click states
        # We expect setIntegerValue to be called 6 times
        calls = mock_quartz.CGEventSetIntegerValueField.call_args_list
        assert len(calls) == 6

        # Check pairs of calls have increasing click states
        # Click 1
        assert calls[0][0][2] == 1
        assert calls[1][0][2] == 1
        # Click 2
        assert calls[2][0][2] == 2
        assert calls[3][0][2] == 2
        # Click 3
        assert calls[4][0][2] == 3
        assert calls[5][0][2] == 3


def test_handler_calls_macos_click_double(mock_pyautogui):
    """Test that handler calls macos_click for double click on macOS."""
    handler = PyautoguiActionHandler()
    action = Action(type=ActionType.LEFT_DOUBLE, argument="500, 500", count=1)

    with (
        patch.object(sys, "platform", "darwin"),
        patch("oagi.handler.pyautogui_action_handler._macos") as mock_macos_module,
    ):
        handler([action])

        mock_macos_module.macos_click.assert_called_once_with(960, 540, clicks=2)
        mock_pyautogui.doubleClick.assert_not_called()


def test_handler_calls_macos_click_triple(mock_pyautogui):
    """Test that handler calls macos_click for triple click on macOS."""
    handler = PyautoguiActionHandler()
    action = Action(type=ActionType.LEFT_TRIPLE, argument="500, 500", count=1)

    with (
        patch.object(sys, "platform", "darwin"),
        patch("oagi.handler.pyautogui_action_handler._macos") as mock_macos_module,
    ):
        handler([action])

        mock_macos_module.macos_click.assert_called_once_with(960, 540, clicks=3)
        mock_pyautogui.tripleClick.assert_not_called()
