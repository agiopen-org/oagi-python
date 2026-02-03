# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import pytest

from oagi.converters import ConverterConfig, OagiActionConverter
from oagi.types import Action, ActionType


@pytest.fixture
def config():
    return ConverterConfig(sandbox_width=1920, sandbox_height=1080)


@pytest.fixture
def converter(config):
    return OagiActionConverter(config=config)


class TestCoordinateBasedActions:
    @pytest.mark.parametrize(
        "action_type,argument,expected_cmd",
        [
            (ActionType.CLICK, "500, 300", "pyautogui.click(x=960, y=324)"),
            (ActionType.LEFT_DOUBLE, "400, 250", "pyautogui.doubleClick(x=768, y=270)"),
            (ActionType.LEFT_TRIPLE, "350, 200", "pyautogui.tripleClick(x=672, y=216)"),
            (
                ActionType.RIGHT_SINGLE,
                "600, 400",
                "pyautogui.rightClick(x=1152, y=432)",
            ),
        ],
    )
    def test_click_actions(self, converter, action_type, argument, expected_cmd):
        action = Action(type=action_type, argument=argument, count=1)
        result = converter([action])
        assert len(result) == 1
        assert result[0] == expected_cmd


class TestDragAction:
    def test_drag_generates_two_commands(self, converter, config):
        action = Action(type=ActionType.DRAG, argument="100, 100, 500, 300", count=1)
        result = converter([action])
        assert len(result) == 2
        assert "pyautogui.moveTo(192, 108)" in result[0]
        assert (
            f"pyautogui.dragTo(960, 324, duration={config.drag_duration})" in result[1]
        )


class TestHotkeyAction:
    def test_hotkey_conversion(self, converter, config):
        action = Action(type=ActionType.HOTKEY, argument="ctrl+c", count=1)
        result = converter([action])
        assert len(result) == 1
        assert (
            f"pyautogui.hotkey('ctrl', 'c', interval={config.hotkey_interval})"
            in result[0]
        )


class TestTypeAction:
    def test_type_conversion(self, converter):
        action = Action(type=ActionType.TYPE, argument="Hello World", count=1)
        result = converter([action])
        assert len(result) == 1
        assert "pyautogui.typewrite" in result[0]
        assert "Hello World" in result[0]


class TestScrollAction:
    @pytest.mark.parametrize("direction,expected_amount", [("up", 2), ("down", -2)])
    def test_scroll_conversion(self, converter, direction, expected_amount):
        action = Action(
            type=ActionType.SCROLL, argument=f"500, 300, {direction}", count=1
        )
        result = converter([action])
        assert len(result) == 2
        assert "pyautogui.moveTo(960, 324)" in result[0]
        assert f"pyautogui.scroll({expected_amount})" in result[1]


class TestSpecialActions:
    def test_wait_action(self, converter, config):
        action = Action(type=ActionType.WAIT, argument="", count=1)
        result = converter([action])
        assert f"WAIT({config.wait_duration})" in result[0]

    def test_finish_action(self, converter):
        action = Action(type=ActionType.FINISH, argument="", count=1)
        result = converter([action])
        assert result[0] == "DONE"


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
        # All should be the same click command
        assert all(cmd == "pyautogui.click(x=960, y=324)" for cmd in result)


class TestStrictCoordinateValidation:
    @pytest.fixture
    def strict_converter(self):
        config = ConverterConfig(
            sandbox_width=1920,
            sandbox_height=1080,
            strict_coordinate_validation=True,
        )
        return OagiActionConverter(config=config)

    @pytest.mark.parametrize(
        "argument,match_pattern",
        [
            ("-10, 500", "x coordinate .* out of valid range"),
            ("500, -10", "y coordinate .* out of valid range"),
            ("1050, 500", "x coordinate .* out of valid range"),
            ("500, 1050", "y coordinate .* out of valid range"),
        ],
    )
    def test_strict_mode_rejects_out_of_range(
        self, strict_converter, argument, match_pattern
    ):
        action = Action(type=ActionType.CLICK, argument=argument, count=1)
        with pytest.raises(RuntimeError, match=match_pattern):
            strict_converter([action])

    def test_non_strict_mode_clamps_out_of_range(self, converter):
        action = Action(type=ActionType.CLICK, argument="1050, 1050", count=1)
        result = converter([action])
        assert "pyautogui.click(x=1919, y=1079)" in result[0]

    @pytest.mark.parametrize(
        "action_type,argument",
        [
            (ActionType.DRAG, "500, 500, 1100, 500"),
            (ActionType.SCROLL, "1100, 500, up"),
        ],
    )
    def test_strict_mode_for_other_actions(
        self, strict_converter, action_type, argument
    ):
        action = Action(type=action_type, argument=argument, count=1)
        with pytest.raises(RuntimeError, match="x coordinate .* out of valid range"):
            strict_converter([action])
