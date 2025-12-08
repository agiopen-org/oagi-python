# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import pytest

from oagi.types import ActionType, Step
from oagi.utils.output_parser import _parse_action, _split_actions, parse_raw_output


class TestParseRawOutput:
    """Test parse_raw_output function."""

    def test_parse_single_click_action(self):
        raw = "<|think_start|>Click the button<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>"
        step = parse_raw_output(raw)

        assert step.reason == "Click the button"
        assert len(step.actions) == 1
        assert step.actions[0].type == ActionType.CLICK
        assert step.actions[0].argument == "300, 150"
        assert step.stop is False

    def test_parse_finish_action_sets_stop(self):
        raw = "<|think_start|>Task complete<|think_end|>\n<|action_start|>finish()<|action_end|>"
        step = parse_raw_output(raw)

        assert step.reason == "Task complete"
        assert len(step.actions) == 1
        assert step.actions[0].type == ActionType.FINISH
        assert step.stop is True

    def test_parse_multiple_actions_with_ampersand(self):
        raw = "<|think_start|>Do two things<|think_end|>\n<|action_start|>click(100, 200) & type(hello)<|action_end|>"
        step = parse_raw_output(raw)

        assert step.reason == "Do two things"
        assert len(step.actions) == 2
        assert step.actions[0].type == ActionType.CLICK
        assert step.actions[1].type == ActionType.TYPE

    def test_parse_empty_output(self):
        step = parse_raw_output("")

        assert step.reason == ""
        assert step.actions == []
        assert step.stop is False

    def test_parse_missing_think_tags(self):
        raw = "<|action_start|>click(100, 200)<|action_end|>"
        step = parse_raw_output(raw)

        assert step.reason == ""
        assert len(step.actions) == 1
        assert step.actions[0].type == ActionType.CLICK

    def test_parse_missing_action_tags(self):
        raw = "<|think_start|>Just thinking<|think_end|>"
        step = parse_raw_output(raw)

        assert step.reason == "Just thinking"
        assert step.actions == []
        assert step.stop is False

    def test_parse_multiline_reason(self):
        raw = "<|think_start|>First line\nSecond line\nThird line<|think_end|>\n<|action_start|>click(100, 200)<|action_end|>"
        step = parse_raw_output(raw)

        assert "First line" in step.reason
        assert "Second line" in step.reason
        assert "Third line" in step.reason

    def test_parse_all_action_types(self):
        raw = """<|think_start|>Test all actions<|think_end|>
<|action_start|>click(100, 200) & left_double(200, 300) & left_triple(300, 400) & right_single(400, 500) & drag(100, 100, 500, 500) & hotkey(ctrl+c) & type(hello) & scroll(500, 300, up) & wait() & finish()<|action_end|>"""
        step = parse_raw_output(raw)

        assert len(step.actions) == 10
        assert step.actions[0].type == ActionType.CLICK
        assert step.actions[1].type == ActionType.LEFT_DOUBLE
        assert step.actions[2].type == ActionType.LEFT_TRIPLE
        assert step.actions[3].type == ActionType.RIGHT_SINGLE
        assert step.actions[4].type == ActionType.DRAG
        assert step.actions[5].type == ActionType.HOTKEY
        assert step.actions[6].type == ActionType.TYPE
        assert step.actions[7].type == ActionType.SCROLL
        assert step.actions[8].type == ActionType.WAIT
        assert step.actions[9].type == ActionType.FINISH
        assert step.stop is True

    def test_parse_invalid_action_skipped(self):
        raw = "<|think_start|>Test<|think_end|>\n<|action_start|>click(100, 200) & invalid_action() & type(hello)<|action_end|>"
        step = parse_raw_output(raw)

        assert len(step.actions) == 2
        assert step.actions[0].type == ActionType.CLICK
        assert step.actions[1].type == ActionType.TYPE


class TestSplitActions:
    """Test _split_actions function."""

    def test_split_single_action(self):
        result = _split_actions("click(100, 200)")
        assert result == ["click(100, 200)"]

    def test_split_multiple_actions(self):
        result = _split_actions("click(100, 200) & type(hello)")
        assert result == ["click(100, 200)", "type(hello)"]

    def test_split_preserves_nested_parentheses(self):
        result = _split_actions("type(func(a, b)) & click(100, 200)")
        assert result == ["type(func(a, b))", "click(100, 200)"]

    def test_split_empty_string(self):
        result = _split_actions("")
        assert result == []

    def test_split_whitespace_handling(self):
        result = _split_actions("  click(100, 200)   &   type(hello)  ")
        assert result == ["click(100, 200)", "type(hello)"]

    def test_split_no_ampersand(self):
        result = _split_actions("click(100, 200)")
        assert result == ["click(100, 200)"]

    def test_split_three_actions(self):
        result = _split_actions("click(100, 200) & type(hello) & finish()")
        assert result == ["click(100, 200)", "type(hello)", "finish()"]


class TestParseAction:
    """Test _parse_action function."""

    @pytest.mark.parametrize(
        "action_text,expected_type,expected_arg",
        [
            ("click(100, 200)", ActionType.CLICK, "100, 200"),
            ("left_double(100, 200)", ActionType.LEFT_DOUBLE, "100, 200"),
            ("left_triple(100, 200)", ActionType.LEFT_TRIPLE, "100, 200"),
            ("right_single(100, 200)", ActionType.RIGHT_SINGLE, "100, 200"),
            ("drag(100, 100, 500, 500)", ActionType.DRAG, "100, 100, 500, 500"),
            ("type(hello world)", ActionType.TYPE, "hello world"),
            ("wait()", ActionType.WAIT, ""),
            ("finish()", ActionType.FINISH, ""),
        ],
    )
    def test_parse_basic_actions(self, action_text, expected_type, expected_arg):
        action = _parse_action(action_text)
        assert action is not None
        assert action.type == expected_type
        assert action.argument == expected_arg
        assert action.count == 1

    def test_parse_hotkey_with_count(self):
        action = _parse_action("hotkey(ctrl+c, 3)")
        assert action is not None
        assert action.type == ActionType.HOTKEY
        assert action.argument == "ctrl+c"
        assert action.count == 3

    def test_parse_hotkey_without_count(self):
        action = _parse_action("hotkey(ctrl+c)")
        assert action is not None
        assert action.type == ActionType.HOTKEY
        assert action.argument == "ctrl+c"
        assert action.count == 1

    def test_parse_scroll_with_count(self):
        action = _parse_action("scroll(500, 300, up, 5)")
        assert action is not None
        assert action.type == ActionType.SCROLL
        assert action.argument == "500,300,up"
        assert action.count == 5

    def test_parse_scroll_without_count(self):
        action = _parse_action("scroll(500, 300, down)")
        assert action is not None
        assert action.type == ActionType.SCROLL
        assert action.argument == "500, 300, down"
        assert action.count == 1

    def test_parse_invalid_action_type(self):
        action = _parse_action("invalid_action(123)")
        assert action is None

    def test_parse_malformed_syntax_no_parens(self):
        action = _parse_action("click 100, 200")
        assert action is None

    def test_parse_empty_string(self):
        action = _parse_action("")
        assert action is None

    def test_parse_uppercase_action(self):
        action = _parse_action("CLICK(100, 200)")
        assert action is not None
        assert action.type == ActionType.CLICK

    def test_parse_scroll_invalid_count_defaults_to_one(self):
        action = _parse_action("scroll(500, 300, up, abc)")
        assert action is not None
        assert action.count == 1

    def test_parse_hotkey_invalid_count_defaults_to_one(self):
        action = _parse_action("hotkey(ctrl+c, abc)")
        assert action is not None
        assert action.count == 1


class TestEdgeCases:
    """Test edge cases and robustness."""

    def test_parse_extra_whitespace(self):
        raw = "  <|think_start|>  thinking  <|think_end|>  \n  <|action_start|>  click(100, 200)  <|action_end|>  "
        step = parse_raw_output(raw)

        assert step.reason == "thinking"
        assert len(step.actions) == 1

    def test_parse_type_with_special_characters(self):
        raw = "<|think_start|>Type special<|think_end|>\n<|action_start|>type(!@#$%^*())<|action_end|>"
        step = parse_raw_output(raw)

        assert len(step.actions) == 1
        assert step.actions[0].argument == "!@#$%^*()"

    def test_parse_type_with_spaces(self):
        raw = "<|think_start|>Type text<|think_end|>\n<|action_start|>type(hello world 123)<|action_end|>"
        step = parse_raw_output(raw)

        assert step.actions[0].argument == "hello world 123"

    def test_returns_step_type(self):
        raw = "<|think_start|>Test<|think_end|>\n<|action_start|>click(100, 200)<|action_end|>"
        step = parse_raw_output(raw)

        assert isinstance(step, Step)

    def test_multiple_finish_actions_stop_true(self):
        raw = "<|think_start|>Test<|think_end|>\n<|action_start|>finish() & finish()<|action_end|>"
        step = parse_raw_output(raw)

        assert step.stop is True
        assert len(step.actions) == 2

    def test_finish_with_other_actions(self):
        raw = "<|think_start|>Test<|think_end|>\n<|action_start|>click(100, 200) & finish()<|action_end|>"
        step = parse_raw_output(raw)

        assert step.stop is True
        assert len(step.actions) == 2
