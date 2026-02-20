# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import sys
from unittest.mock import patch

import pytest

from oagi import AsyncPyautoguiActionHandler
from oagi.handler.capslock_manager import CapsLockManager
from oagi.handler.pyautogui_action_handler import (
    PyautoguiActionHandler,
    PyautoguiConfig,
)
from oagi.handler.utils import configure_handler_delay
from oagi.types import Action, ActionType


@pytest.fixture
def mock_pyautogui():
    with patch("oagi.handler.pyautogui_action_handler.pyautogui") as mock:
        mock.size.return_value = (1920, 1080)
        yield mock


@pytest.fixture
def config():
    # Disable post_batch_delay to avoid sleeping in tests
    return PyautoguiConfig(post_batch_delay=0)


@pytest.fixture
def handler(mock_pyautogui):
    # Disable post_batch_delay to avoid sleeping in tests
    return PyautoguiActionHandler(config=PyautoguiConfig(post_batch_delay=0))


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
    # Mock platform as Linux to ensure standard methods are called (not macOS specific ones)
    with patch.object(sys, "platform", "linux"):
        action = Action(type=action_type, argument=argument, count=1)
        handler([action])

        # Click actions now use moveTo first, then click without coordinates
        mock_pyautogui.moveTo.assert_called_with(*expected_coords)
        getattr(mock_pyautogui, expected_method).assert_called_once_with()


def test_drag_action(handler, mock_pyautogui, config):
    action = Action(type=ActionType.DRAG, argument="100, 100, 500, 300", count=1)
    handler([action])

    mock_pyautogui.moveTo.assert_any_call(192, 108)
    mock_pyautogui.dragTo.assert_called_once_with(
        960, 324, duration=config.drag_duration, button="left"
    )


def test_mouse_move_action(handler, mock_pyautogui):
    action = Action(type=ActionType.MOUSE_MOVE, argument="500, 300", count=1)
    handler([action])
    mock_pyautogui.moveTo.assert_called_once_with(960, 324)


def test_left_click_drag_action(handler, mock_pyautogui, config):
    action = Action(type=ActionType.LEFT_CLICK_DRAG, argument="500, 300", count=1)
    handler([action])
    mock_pyautogui.dragTo.assert_called_once_with(
        960, 324, duration=config.drag_duration, button="left"
    )


def test_press_click_action(handler, mock_pyautogui):
    action = Action(
        type=ActionType.PRESS_CLICK,
        argument='{"keys":["ctrl"],"click_type":"left_click","coordinate":[500,300]}',
        count=1,
    )
    handler([action])

    mock_pyautogui.keyDown.assert_called_once_with("ctrl")
    mock_pyautogui.moveTo.assert_called_once_with(960, 324)
    mock_pyautogui.click.assert_called_once_with()
    mock_pyautogui.keyUp.assert_called_once_with("ctrl")


def test_hotkey_action(mock_pyautogui):
    # Disable macos_ctrl_to_cmd to test basic hotkey functionality
    config = PyautoguiConfig(macos_ctrl_to_cmd=False)
    handler = PyautoguiActionHandler(config=config)
    action = Action(type=ActionType.HOTKEY, argument="ctrl+c", count=1)
    handler([action])

    mock_pyautogui.hotkey.assert_called_once_with(
        "ctrl", "c", interval=config.hotkey_interval
    )


def test_type_action(handler, mock_pyautogui):
    # Mock platform as Linux to use pyautogui.typewrite fallback
    with patch.object(sys, "platform", "linux"):
        action = Action(type=ActionType.TYPE, argument="Hello World", count=1)
        handler([action])

        mock_pyautogui.typewrite.assert_called_once_with("Hello World")


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
        # wait_duration calls time.sleep (post_batch_delay is 0 in test fixture)
        mock_sleep.assert_called_once_with(config.wait_duration)


def test_hotkey_with_custom_interval(mock_pyautogui):
    custom_config = PyautoguiConfig(hotkey_interval=0.5)
    handler = PyautoguiActionHandler(config=custom_config)

    action = Action(type=ActionType.HOTKEY, argument="cmd+shift+a", count=1)
    handler([action])

    mock_pyautogui.hotkey.assert_called_once_with("cmd", "shift", "a", interval=0.5)


def test_finish_action(handler, mock_pyautogui):
    action = Action(type=ActionType.FINISH, argument="", count=1)
    handler([action])


def test_fail_action(handler, mock_pyautogui):
    action = Action(type=ActionType.FAIL, argument="", count=1)
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

    def test_multiple_actions(self, mock_pyautogui):
        # Disable macos_ctrl_to_cmd to test basic hotkey functionality
        # Mock platform as Linux to use pyautogui.typewrite fallback
        config = PyautoguiConfig(macos_ctrl_to_cmd=False)
        handler = PyautoguiActionHandler(config=config)
        actions = [
            Action(type=ActionType.CLICK, argument="100, 100", count=1),
            Action(type=ActionType.TYPE, argument="test", count=1),
            Action(type=ActionType.HOTKEY, argument="ctrl+s", count=1),
        ]
        with patch.object(sys, "platform", "linux"):
            handler(actions)

        mock_pyautogui.click.assert_called_once()
        mock_pyautogui.typewrite.assert_called_once_with("test")
        mock_pyautogui.hotkey.assert_called_once_with("ctrl", "s", interval=0.1)


class TestInputValidation:
    def test_invalid_coordinates_format(self, handler, mock_pyautogui):
        action = Action(type=ActionType.CLICK, argument="invalid", count=1)

        with pytest.raises(ValueError, match="Invalid coordinates format"):
            handler([action])

    def test_type_with_quotes(self, handler, mock_pyautogui):
        # Mock platform as Linux to use pyautogui.typewrite fallback
        with patch.object(sys, "platform", "linux"):
            action = Action(type=ActionType.TYPE, argument='"Hello World"', count=1)
            handler([action])

            mock_pyautogui.typewrite.assert_called_once_with("Hello World")


class TestCapsLockManager:
    def test_session_mode_text_transformation(self):
        manager = CapsLockManager(mode="session")

        # Initially caps is off
        assert manager.transform_text("Hello World") == "Hello World"
        assert manager.transform_text("123!@#") == "123!@#"

        # Toggle caps on
        manager.toggle()
        assert manager.caps_enabled is True
        assert manager.transform_text("Hello World") == "HELLO WORLD"
        assert manager.transform_text("test123!") == "TEST123!"
        assert manager.transform_text("123!@#") == "123!@#"

        # Toggle caps off
        manager.toggle()
        assert manager.caps_enabled is False
        assert manager.transform_text("Hello World") == "Hello World"

    def test_system_mode_no_transformation(self):
        manager = CapsLockManager(mode="system")

        # System mode doesn't transform text
        assert manager.transform_text("Hello World") == "Hello World"

        manager.toggle()  # Should not affect state in system mode
        assert manager.caps_enabled is False
        assert manager.transform_text("Hello World") == "Hello World"

    def test_should_use_system_capslock(self):
        session_manager = CapsLockManager(mode="session")
        system_manager = CapsLockManager(mode="system")

        assert session_manager.should_use_system_capslock() is False
        assert system_manager.should_use_system_capslock() is True

    def test_reset_method(self):
        manager = CapsLockManager(mode="session")

        # Enable caps lock
        manager.toggle()
        assert manager.caps_enabled is True

        # Reset should set caps_enabled to False
        manager.reset()
        assert manager.caps_enabled is False

        # Toggle again and reset
        manager.toggle()
        manager.toggle()  # Back to True
        manager.toggle()  # Now True again
        assert manager.caps_enabled is True
        manager.reset()
        assert manager.caps_enabled is False


class TestCornerCoordinatesHandling:
    """Test that corner coordinates are adjusted to prevent PyAutoGUI fail-safe."""

    @pytest.mark.parametrize(
        "input_coords,expected_coords",
        [
            # Top-left corner
            ("0, 0", (1, 1)),
            ("1, 1", (2, 1)),
            # Top-right corner (assuming 1920x1080 screen)
            ("1000, 0", (1918, 1)),
            ("999, 1", (1918, 1)),
            # Bottom-left corner
            ("0, 1000", (1, 1078)),
            ("1, 999", (2, 1078)),
            # Bottom-right corner
            ("1000, 1000", (1918, 1078)),
            ("999, 999", (1918, 1078)),
            # Middle coordinates should not be affected
            ("500, 500", (960, 540)),
            ("250, 750", (480, 810)),
        ],
    )
    def test_corner_coordinate_adjustment(
        self, mock_pyautogui, input_coords, expected_coords
    ):
        handler = PyautoguiActionHandler(config=PyautoguiConfig(post_batch_delay=0))
        action = Action(type=ActionType.CLICK, argument=input_coords, count=1)
        handler([action])
        # Click actions now use moveTo first, then click without coordinates
        mock_pyautogui.moveTo.assert_called_with(*expected_coords)
        mock_pyautogui.click.assert_called_once_with()

    def test_drag_with_corner_coordinates(self, mock_pyautogui, config):
        """Test drag operations with corner coordinates."""
        handler = PyautoguiActionHandler(config=config)
        # Drag from top-left corner to bottom-right corner
        action = Action(type=ActionType.DRAG, argument="0, 0, 1000, 1000", count=1)
        handler([action])

        # Should adjust corner coordinates to prevent fail-safe
        mock_pyautogui.moveTo.assert_called_once_with(1, 1)
        mock_pyautogui.dragTo.assert_called_once_with(
            1918, 1078, duration=config.drag_duration, button="left"
        )

    def test_scroll_with_corner_coordinates(self, mock_pyautogui, config):
        """Test scroll operations at corner coordinates."""
        handler = PyautoguiActionHandler(config=config)
        action = Action(type=ActionType.SCROLL, argument="0, 0, up", count=1)
        handler([action])

        # Should adjust corner coordinates
        mock_pyautogui.moveTo.assert_called_once_with(1, 1)
        mock_pyautogui.scroll.assert_called_once_with(config.scroll_amount)

    def test_multiple_clicks_at_corners(self, mock_pyautogui):
        """Test multiple clicks at corner positions."""
        handler = PyautoguiActionHandler(config=PyautoguiConfig(post_batch_delay=0))
        actions = [
            Action(type=ActionType.LEFT_DOUBLE, argument="0, 0", count=1),
            Action(type=ActionType.LEFT_TRIPLE, argument="1000, 0", count=1),
            Action(type=ActionType.RIGHT_SINGLE, argument="0, 1000", count=1),
        ]

        # Mock platform as Linux to ensure standard methods are called
        with patch.object(sys, "platform", "linux"):
            handler(actions)

            # All click actions now use moveTo first, then click without coordinates
            # Check moveTo was called with the adjusted corner coordinates
            moveTo_calls = mock_pyautogui.moveTo.call_args_list
            assert (1, 1) in [call[0] for call in moveTo_calls]
            assert (1918, 1) in [call[0] for call in moveTo_calls]
            assert (1, 1078) in [call[0] for call in moveTo_calls]
            # Click methods called without coordinates
            mock_pyautogui.doubleClick.assert_called_once_with()
            mock_pyautogui.tripleClick.assert_called_once_with()
            mock_pyautogui.rightClick.assert_called_once_with()


class TestCapsLockIntegration:
    def test_caps_lock_key_normalization(self, mock_pyautogui):
        handler = PyautoguiActionHandler(config=PyautoguiConfig(post_batch_delay=0))

        # Test different caps lock variations
        for variant in ["caps", "caps_lock", "capslock"]:
            keys = handler._parse_hotkey(variant)
            assert keys == ["capslock"]

    def test_caps_lock_session_mode(self, mock_pyautogui):
        config = PyautoguiConfig(capslock_mode="session", post_batch_delay=0)
        handler = PyautoguiActionHandler(config=config)

        # Mock platform as Linux to use pyautogui.typewrite fallback
        with patch.object(sys, "platform", "linux"):
            # Type without caps
            type_action = Action(type=ActionType.TYPE, argument="test", count=1)
            handler([type_action])
            mock_pyautogui.typewrite.assert_called_with("test")

            # Toggle caps lock
            caps_action = Action(type=ActionType.HOTKEY, argument="caps_lock", count=1)
            handler([caps_action])
            # In session mode, should not call pyautogui.hotkey for capslock
            assert mock_pyautogui.hotkey.call_count == 0

            # Type with caps enabled
            mock_pyautogui.typewrite.reset_mock()
            type_action = Action(type=ActionType.TYPE, argument="test", count=1)
            handler([type_action])
            mock_pyautogui.typewrite.assert_called_with("TEST")

    def test_caps_lock_system_mode(self, mock_pyautogui):
        config = PyautoguiConfig(capslock_mode="system", post_batch_delay=0)
        handler = PyautoguiActionHandler(config=config)

        # Toggle caps lock in system mode
        caps_action = Action(type=ActionType.HOTKEY, argument="caps", count=1)
        handler([caps_action])
        # In system mode, should call pyautogui.hotkey
        mock_pyautogui.hotkey.assert_called_once_with("capslock", interval=0.1)

        # Mock platform as Linux to use pyautogui.typewrite fallback
        with patch.object(sys, "platform", "linux"):
            # Type action should not transform text in system mode
            mock_pyautogui.typewrite.reset_mock()
            type_action = Action(type=ActionType.TYPE, argument="test", count=1)
            handler([type_action])
            mock_pyautogui.typewrite.assert_called_with("test")

    def test_regular_hotkey_not_affected(self, mock_pyautogui):
        # Disable macos_ctrl_to_cmd to test basic hotkey functionality
        config = PyautoguiConfig(macos_ctrl_to_cmd=False, post_batch_delay=0)
        handler = PyautoguiActionHandler(config=config)

        # Regular hotkeys should work normally
        action = Action(type=ActionType.HOTKEY, argument="ctrl+c", count=1)
        handler([action])
        mock_pyautogui.hotkey.assert_called_once_with("ctrl", "c", interval=0.1)


class TestMacosCtrlToCmd:
    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_ctrl_remapped_to_command_on_macos_by_default(self, mock_pyautogui):
        handler = PyautoguiActionHandler(config=PyautoguiConfig(post_batch_delay=0))
        action = Action(type=ActionType.HOTKEY, argument="ctrl+c", count=1)
        handler([action])
        mock_pyautogui.hotkey.assert_called_once_with("command", "c", interval=0.1)

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_ctrl_not_remapped_when_disabled(self, mock_pyautogui):
        config = PyautoguiConfig(macos_ctrl_to_cmd=False, post_batch_delay=0)
        handler = PyautoguiActionHandler(config=config)
        action = Action(type=ActionType.HOTKEY, argument="ctrl+c", count=1)
        handler([action])
        mock_pyautogui.hotkey.assert_called_once_with("ctrl", "c", interval=0.1)

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_multiple_keys_with_ctrl_remapped(self, mock_pyautogui):
        handler = PyautoguiActionHandler(config=PyautoguiConfig(post_batch_delay=0))
        action = Action(type=ActionType.HOTKEY, argument="ctrl+shift+a", count=1)
        handler([action])
        mock_pyautogui.hotkey.assert_called_once_with(
            "command", "shift", "a", interval=0.1
        )

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_cmd_not_affected_on_macos(self, mock_pyautogui):
        handler = PyautoguiActionHandler(config=PyautoguiConfig(post_batch_delay=0))
        action = Action(type=ActionType.HOTKEY, argument="cmd+v", count=1)
        handler([action])
        mock_pyautogui.hotkey.assert_called_once_with("cmd", "v", interval=0.1)

    def test_ctrl_not_remapped_on_non_macos(self, mock_pyautogui):
        with patch.object(sys, "platform", "linux"):
            handler = PyautoguiActionHandler(config=PyautoguiConfig(post_batch_delay=0))
            action = Action(type=ActionType.HOTKEY, argument="ctrl+c", count=1)
            handler([action])
            mock_pyautogui.hotkey.assert_called_once_with("ctrl", "c", interval=0.1)

    def test_other_keys_not_affected(self, mock_pyautogui):
        handler = PyautoguiActionHandler(config=PyautoguiConfig(post_batch_delay=0))
        action = Action(type=ActionType.HOTKEY, argument="shift+tab", count=1)
        handler([action])
        mock_pyautogui.hotkey.assert_called_once_with("shift", "tab", interval=0.1)


class TestHandlerReset:
    def test_handler_reset_resets_capslock_state(self, mock_pyautogui):
        config = PyautoguiConfig(capslock_mode="session", post_batch_delay=0)
        handler = PyautoguiActionHandler(config=config)

        # Enable caps lock via hotkey
        caps_action = Action(type=ActionType.HOTKEY, argument="capslock", count=1)
        handler([caps_action])
        assert handler.caps_manager.caps_enabled is True

        # Reset handler
        handler.reset()
        assert handler.caps_manager.caps_enabled is False

    def test_finish_action_resets_handler(self, mock_pyautogui):
        config = PyautoguiConfig(capslock_mode="session", post_batch_delay=0)
        handler = PyautoguiActionHandler(config=config)

        # Enable caps lock
        caps_action = Action(type=ActionType.HOTKEY, argument="capslock", count=1)
        handler([caps_action])
        assert handler.caps_manager.caps_enabled is True

        # FINISH action should reset handler
        finish_action = Action(type=ActionType.FINISH, argument="", count=1)
        handler([finish_action])
        assert handler.caps_manager.caps_enabled is False

    def test_fail_action_resets_handler(self, mock_pyautogui):
        config = PyautoguiConfig(capslock_mode="session", post_batch_delay=0)
        handler = PyautoguiActionHandler(config=config)

        # Enable caps lock
        caps_action = Action(type=ActionType.HOTKEY, argument="capslock", count=1)
        handler([caps_action])
        assert handler.caps_manager.caps_enabled is True

        # FAIL action should also reset handler
        fail_action = Action(type=ActionType.FAIL, argument="", count=1)
        handler([fail_action])
        assert handler.caps_manager.caps_enabled is False


class TestAsyncHandlerReset:
    def test_async_handler_reset_delegates_to_sync_handler(self, mock_pyautogui):
        config = PyautoguiConfig(capslock_mode="session", post_batch_delay=0)
        handler = AsyncPyautoguiActionHandler(config=config)

        # Enable caps lock on the underlying sync handler
        handler.sync_handler.caps_manager.toggle()
        assert handler.sync_handler.caps_manager.caps_enabled is True

        # Reset via async handler
        handler.reset()
        assert handler.sync_handler.caps_manager.caps_enabled is False


class TestConfigureHandlerDelay:
    def test_configure_handler_delay(self, mock_pyautogui):
        handler = PyautoguiActionHandler()
        original_delay = handler.config.post_batch_delay

        configure_handler_delay(handler, 3.0)
        assert handler.config.post_batch_delay == 3.0
        assert handler.config.post_batch_delay != original_delay

    def test_configure_handler_delay_with_zero(self, mock_pyautogui):
        handler = PyautoguiActionHandler()
        configure_handler_delay(handler, 0)
        assert handler.config.post_batch_delay == 0

    def test_configure_handler_delay_ignores_incompatible_handler(self):
        # A handler without config attribute
        class DummyHandler:
            pass

        handler = DummyHandler()
        # Should not raise
        configure_handler_delay(handler, 1.0)
