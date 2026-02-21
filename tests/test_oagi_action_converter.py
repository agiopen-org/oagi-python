# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import logging

import pytest

from oagi.converters import OagiActionConverter, PyautoguiActionConvertor
from oagi.types import Action, ActionType


@pytest.fixture
def converter():
    return PyautoguiActionConvertor(logger=logging.getLogger("test"))


def _cmds(result: list[tuple[str, bool]]) -> list[str]:
    """Extract command strings from converter result tuples."""
    return [cmd for cmd, _ in result]


class TestBackwardCompatAlias:
    def test_oagi_action_converter_is_alias(self):
        assert OagiActionConverter is PyautoguiActionConvertor


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
        ids=["click", "double-click", "triple-click", "right-click"],
    )
    def test_click_actions(self, converter, action_type, argument, expected_cmd):
        action = Action(type=action_type, argument=argument, count=1)
        result = converter([action])
        assert len(result) == 1
        cmd, is_last = result[0]
        assert cmd == expected_cmd
        assert is_last is True


class TestDragAction:
    def test_drag_generates_two_commands(self, converter):
        action = Action(type=ActionType.DRAG, argument="100, 100, 500, 300", count=1)
        result = converter([action])
        cmds = _cmds(result)
        assert len(cmds) == 2
        assert "pyautogui.moveTo(192, 108)" in cmds[0]
        assert "pyautogui.dragTo(960, 324, duration=0.5)" in cmds[1]
        # Only last command should have is_last=True
        assert result[0][1] is False
        assert result[1][1] is True


class TestHotkeyAction:
    def test_hotkey_conversion(self, converter):
        action = Action(type=ActionType.HOTKEY, argument="ctrl+c", count=1)
        result = converter([action])
        cmds = _cmds(result)
        assert len(cmds) == 1
        assert "pyautogui.hotkey('ctrl', 'c', interval=0.1)" in cmds[0]


class TestTypeAction:
    def test_short_ascii_uses_pynput(self, converter):
        action = Action(type=ActionType.TYPE, argument="Hello World", count=1)
        result = converter([action])
        cmds = _cmds(result)
        assert len(cmds) == 1
        assert "PynputController().type('Hello World')" == cmds[0]

    def test_unicode_uses_smart_paste(self, converter):
        action = Action(type=ActionType.TYPE, argument="你好世界", count=1)
        result = converter([action])
        cmds = _cmds(result)
        assert len(cmds) == 1
        assert "_smart_paste('你好世界')" == cmds[0]

    def test_multiline_uses_smart_paste(self, converter):
        action = Action(type=ActionType.TYPE, argument="line1\nline2", count=1)
        result = converter([action])
        cmds = _cmds(result)
        assert len(cmds) == 1
        assert "_smart_paste(" in cmds[0]

    def test_long_text_uses_smart_paste(self, converter):
        long_text = "a" * 201
        action = Action(type=ActionType.TYPE, argument=long_text, count=1)
        result = converter([action])
        cmds = _cmds(result)
        assert len(cmds) == 1
        assert "_smart_paste(" in cmds[0]

    @pytest.mark.parametrize(
        "argument,expected_substr",
        [
            (" ", " "),
            ('"Hello World"', '"Hello World"'),
            ("it's a test", "it's a test"),
            ('"reportMissingImports": "none"', '"reportMissingImports": "none"'),
            ('=TEXT(C2,"0000000")', '=TEXT(C2,"0000000")'),
            ('find . -name "*.php"', 'find . -name "*.php"'),
            (")", ")"),
        ],
        ids=[
            "space",
            "double-quoted-text",
            "apostrophe",
            "json-config",
            "excel-formula",
            "shell-find",
            "right-paren",
        ],
    )
    def test_type_preserves_content(self, converter, argument, expected_substr):
        """Type content (spaces, quotes, parens) is preserved as literal text."""
        action = Action(type=ActionType.TYPE, argument=argument, count=1)
        result = converter([action])
        cmds = _cmds(result)
        assert len(cmds) == 1
        assert expected_substr in cmds[0]


class TestScrollAction:
    @pytest.mark.parametrize(
        "direction,expected_amount",
        [("up", 2), ("down", -2)],
        ids=["scroll-up", "scroll-down"],
    )
    def test_scroll_conversion(self, converter, direction, expected_amount):
        action = Action(
            type=ActionType.SCROLL, argument=f"500, 300, {direction}", count=1
        )
        result = converter([action])
        cmds = _cmds(result)
        assert len(cmds) == 2
        assert "pyautogui.moveTo(960, 324)" in cmds[0]
        assert f"pyautogui.scroll({expected_amount})" in cmds[1]


class TestSpecialActions:
    def test_wait_action(self, converter):
        action = Action(type=ActionType.WAIT, argument="", count=1)
        result = converter([action])
        cmds = _cmds(result)
        assert "WAIT(1.0)" in cmds[0]

    def test_finish_action(self, converter):
        action = Action(type=ActionType.FINISH, argument="", count=1)
        result = converter([action])
        assert result[0][0] == "DONE"

    def test_fail_action(self, converter):
        action = Action(type=ActionType.FAIL, argument="", count=1)
        result = converter([action])
        assert result[0][0] == "FAIL"

    def test_duplicate_terminal_actions_raises(self, converter):
        actions = [
            Action(type=ActionType.FINISH, argument="", count=1),
            Action(type=ActionType.FAIL, argument="", count=1),
        ]
        with pytest.raises(ValueError, match="Duplicate finish\\(\\)/fail\\(\\)"):
            converter(actions)


class TestActionStringToStep:
    def test_pyautogui_command(self, converter):
        step = converter.action_string_to_step("pyautogui.click(x=100, y=200)")
        assert step["type"] == "pyautogui"
        assert step["parameters"]["code"] == "pyautogui.click(x=100, y=200)"

    def test_pynput_command(self, converter):
        step = converter.action_string_to_step("PynputController().type('hello')")
        assert step["type"] == "pyautogui"
        assert step["parameters"]["code"] == "PynputController().type('hello')"

    def test_smart_paste_command(self, converter):
        step = converter.action_string_to_step("_smart_paste('hello')")
        assert step["type"] == "pyautogui"
        assert step["parameters"]["code"] == "_smart_paste('hello')"

    def test_wait_command(self, converter):
        step = converter.action_string_to_step("WAIT(5)")
        assert step["type"] == "sleep"
        assert step["parameters"]["seconds"] == 5.0

    def test_done_command(self, converter):
        step = converter.action_string_to_step("DONE")
        assert step["type"] == "sleep"
        assert step["parameters"]["seconds"] == 0

    def test_fail_command(self, converter):
        step = converter.action_string_to_step("FAIL")
        assert step["type"] == "sleep"
        assert step["parameters"]["seconds"] == 0


class TestMultipleActions:
    def test_action_count(self, converter):
        action = Action(type=ActionType.CLICK, argument="500, 300", count=3)
        result = converter([action])
        cmds = _cmds(result)
        # Each click generates 1 command, repeated 3 times
        assert len(cmds) == 3
        # All should be the same click command
        assert all(cmd == "pyautogui.click(x=960, y=324)" for cmd in cmds)
        # Only the last should have is_last=True
        assert result[0][1] is False
        assert result[1][1] is False
        assert result[2][1] is True

    def test_drag_count(self, converter):
        action = Action(type=ActionType.DRAG, argument="100, 100, 500, 300", count=2)
        result = converter([action])
        # Drag generates 2 commands, repeated 2 times = 4 total
        assert len(result) == 4
        # is_last only on the very last command
        assert [is_last for _, is_last in result] == [False, False, False, True]


class TestCoordinateValidation:
    @pytest.mark.parametrize(
        "argument,match_pattern",
        [
            ("-10, 500", "x coordinate .* out of valid range"),
            ("500, -10", "y coordinate .* out of valid range"),
            ("1050, 500", "x coordinate .* out of valid range"),
            ("500, 1050", "y coordinate .* out of valid range"),
        ],
        ids=["neg-x", "neg-y", "over-x", "over-y"],
    )
    def test_rejects_out_of_range(self, converter, argument, match_pattern):
        action = Action(type=ActionType.CLICK, argument=argument, count=1)
        # Coordinates always validated, wraps in RuntimeError from __call__
        with pytest.raises(RuntimeError, match=match_pattern):
            converter([action])

    def test_boundary_1000_clamps_to_max(self, converter):
        """Coordinates at exactly 1000 are valid but clamped to screen edge."""
        action = Action(type=ActionType.CLICK, argument="1000, 1000", count=1)
        result = converter([action])
        assert result[0][0] == "pyautogui.click(x=1919, y=1079)"

    @pytest.mark.parametrize(
        "action_type,argument",
        [
            (ActionType.DRAG, "500, 500, 1100, 500"),
            (ActionType.SCROLL, "1100, 500, up"),
        ],
        ids=["drag-over-range", "scroll-over-range"],
    )
    def test_other_actions_reject_out_of_range(self, converter, action_type, argument):
        action = Action(type=action_type, argument=argument, count=1)
        with pytest.raises(RuntimeError, match="x coordinate .* out of valid range"):
            converter([action])
