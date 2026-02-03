# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Tests for OagiActionConverter."""

import pytest

from oagi.converters import BaseActionConverter, ConverterConfig, OagiActionConverter
from oagi.types import Action, ActionType


@pytest.fixture
def config():
    return ConverterConfig(sandbox_width=1920, sandbox_height=1080)


@pytest.fixture
def converter(config):
    return OagiActionConverter(config=config)


class TestCoordinateBasedActions:
    """Test actions with coordinates."""

    @pytest.mark.parametrize(
        "action_type,argument,expected_cmd",
        [
            (ActionType.CLICK, "500, 300", "pyautogui.click(x=960, y=324)"),
            (ActionType.LEFT_DOUBLE, "400, 250", "pyautogui.doubleClick(x=768, y=270)"),
            (ActionType.LEFT_TRIPLE, "350, 200", "pyautogui.tripleClick(x=672, y=216)"),
            (ActionType.RIGHT_SINGLE, "600, 400", "pyautogui.rightClick(x=1152, y=432)"),
        ],
    )
    def test_click_actions(self, converter, action_type, argument, expected_cmd):
        action = Action(type=action_type, argument=argument, count=1)
        result = converter([action])
        assert len(result) == 1
        assert result[0][0] == expected_cmd
        assert result[0][1] is True  # is_last


class TestDragAction:
    def test_drag_generates_two_commands(self, converter, config):
        action = Action(type=ActionType.DRAG, argument="100, 100, 500, 300", count=1)
        result = converter([action])
        assert len(result) == 2
        assert "pyautogui.moveTo(192, 108)" in result[0][0]
        assert f"pyautogui.dragTo(960, 324, duration={config.drag_duration})" in result[1][0]


class TestHotkeyAction:
    def test_hotkey_conversion(self, converter, config):
        action = Action(type=ActionType.HOTKEY, argument="ctrl+c", count=1)
        result = converter([action])
        assert len(result) == 1
        assert f"pyautogui.hotkey('ctrl', 'c', interval={config.hotkey_interval})" in result[0][0]


class TestTypeAction:
    def test_type_conversion(self, converter):
        action = Action(type=ActionType.TYPE, argument="Hello World", count=1)
        result = converter([action])
        assert len(result) == 1
        assert "pyautogui.typewrite" in result[0][0]
        assert "Hello World" in result[0][0]


class TestScrollAction:
    @pytest.mark.parametrize("direction,expected_amount", [("up", 2), ("down", -2)])
    def test_scroll_conversion(self, converter, direction, expected_amount):
        action = Action(type=ActionType.SCROLL, argument=f"500, 300, {direction}", count=1)
        result = converter([action])
        assert len(result) == 2
        assert "pyautogui.moveTo(960, 324)" in result[0][0]
        assert f"pyautogui.scroll({expected_amount})" in result[1][0]


class TestSpecialActions:
    def test_wait_action(self, converter, config):
        action = Action(type=ActionType.WAIT, argument="", count=1)
        result = converter([action])
        assert f"WAIT({config.wait_duration})" in result[0][0]

    def test_finish_action(self, converter):
        action = Action(type=ActionType.FINISH, argument="", count=1)
        result = converter([action])
        assert result[0][0] == "DONE"


class TestActionStringToStep:
    def test_pyautogui_command(self, converter):
        step = converter.action_string_to_step("pyautogui.click(x=100, y=200)")
        assert step["type"] == "pyautogui"
        assert step["parameters"]["code"] == "pyautogui.click(x=100, y=200)"

    def test_wait_command(self, converter):
        step = converter.action_string_to_step("WAIT(5)")
        assert step["type"] == "sleep"
        assert step["parameters"]["seconds"] == 5.0

    def test_done_command(self, converter):
        step = converter.action_string_to_step("DONE")
        assert step["type"] == "sleep"
        assert step["parameters"]["seconds"] == 0


class TestMultipleActions:
    def test_action_count(self, converter):
        action = Action(type=ActionType.CLICK, argument="500, 300", count=3)
        result = converter([action])
        # Each click generates 1 command, repeated 3 times
        assert len(result) == 3
        # Only the last one should have is_last=True
        assert result[0][1] is False
        assert result[1][1] is False
        assert result[2][1] is True


class TestBaseActionConverterExports:
    """Test that base class is properly exported for inheritance."""

    def test_base_class_exported(self):
        assert BaseActionConverter is not None

    def test_config_exported(self):
        config = ConverterConfig()
        assert config.sandbox_width == 1920
        assert config.sandbox_height == 1080

    def test_oagi_converter_inherits_base(self, converter):
        assert isinstance(converter, BaseActionConverter)


class TestStrictCoordinateValidation:
    """Test strict coordinate validation mode."""

    @pytest.fixture
    def strict_config(self):
        return ConverterConfig(
            sandbox_width=1920,
            sandbox_height=1080,
            strict_coordinate_validation=True,
        )

    @pytest.fixture
    def strict_converter(self, strict_config):
        return OagiActionConverter(config=strict_config)

    def test_strict_mode_disabled_by_default(self):
        config = ConverterConfig()
        assert config.strict_coordinate_validation is False

    def test_strict_mode_clamps_valid_coordinates(self, strict_converter):
        """Valid coordinates within [0, 1000] should work in strict mode."""
        action = Action(type=ActionType.CLICK, argument="500, 500", count=1)
        result = strict_converter([action])
        assert len(result) == 1
        assert "pyautogui.click" in result[0][0]

    def test_strict_mode_raises_on_negative_x(self, strict_converter):
        """Negative x coordinate should raise error in strict mode."""
        action = Action(type=ActionType.CLICK, argument="-10, 500", count=1)
        with pytest.raises(RuntimeError, match="x coordinate .* out of valid range"):
            strict_converter([action])

    def test_strict_mode_raises_on_negative_y(self, strict_converter):
        """Negative y coordinate should raise error in strict mode."""
        action = Action(type=ActionType.CLICK, argument="500, -10", count=1)
        with pytest.raises(RuntimeError, match="y coordinate .* out of valid range"):
            strict_converter([action])

    def test_strict_mode_raises_on_x_exceeding_max(self, strict_converter):
        """x coordinate > 1000 should raise error in strict mode."""
        action = Action(type=ActionType.CLICK, argument="1050, 500", count=1)
        with pytest.raises(RuntimeError, match="x coordinate .* out of valid range"):
            strict_converter([action])

    def test_strict_mode_raises_on_y_exceeding_max(self, strict_converter):
        """y coordinate > 1000 should raise error in strict mode."""
        action = Action(type=ActionType.CLICK, argument="500, 1050", count=1)
        with pytest.raises(RuntimeError, match="y coordinate .* out of valid range"):
            strict_converter([action])

    def test_non_strict_mode_clamps_out_of_range(self, converter):
        """Non-strict mode should clamp out-of-range coordinates."""
        # This should not raise, coordinates get clamped
        action = Action(type=ActionType.CLICK, argument="1050, 1050", count=1)
        result = converter([action])
        assert len(result) == 1
        # Coordinates should be clamped to max (1919, 1079)
        assert "pyautogui.click(x=1919, y=1079)" in result[0][0]

    def test_strict_mode_for_drag(self, strict_converter):
        """Drag action should also validate coordinates in strict mode."""
        action = Action(type=ActionType.DRAG, argument="500, 500, 1100, 500", count=1)
        with pytest.raises(RuntimeError, match="x coordinate .* out of valid range"):
            strict_converter([action])

    def test_strict_mode_for_scroll(self, strict_converter):
        """Scroll action should also validate coordinates in strict mode."""
        action = Action(type=ActionType.SCROLL, argument="1100, 500, up", count=1)
        with pytest.raises(RuntimeError, match="x coordinate .* out of valid range"):
            strict_converter([action])
