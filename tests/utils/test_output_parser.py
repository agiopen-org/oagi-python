# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import json

import pytest

from oagi.types import ActionType, Step
from oagi.utils.output_parser import _parse_action, _split_actions, parse_raw_output


class TestQwen3Parsing:
    def test_qwen3_default_parser_mode(self):
        raw = """<think>
Need to click the submit button.
</think>
Action: Click the submit button.
<tool_call>
{"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [300, 150]}}
</tool_call>"""

        step = parse_raw_output(raw)

        assert step.reason == "Need to click the submit button."
        assert len(step.actions) == 1
        assert step.actions[0].type == ActionType.CLICK
        assert step.actions[0].argument == "300, 150"
        assert step.stop is False

    def test_qwen3_action_summary_fallback_on_invalid_json(self):
        raw = """Action: Open the file menu.
<tool_call>
{not a json payload}
</tool_call>"""

        step = parse_raw_output(raw)

        assert step.reason == "Open the file menu."
        assert step.actions == []
        assert step.stop is False

    @pytest.mark.parametrize(
        "status,expected_type",
        [
            ("success", ActionType.FINISH),
            ("failure", ActionType.FAIL),
        ],
    )
    def test_qwen3_terminate_status_mapping(self, status, expected_type):
        raw = f"""Action: Finish task.
<tool_call>
{{"name": "computer_use", "arguments": {{"action": "terminate", "status": "{status}"}}}}
</tool_call>"""

        step = parse_raw_output(raw)

        assert len(step.actions) == 1
        assert step.actions[0].type == expected_type
        assert step.stop is True

    def test_qwen3_new_actions(self):
        raw = """Action: Perform combined action.
<tool_call>
{"name": "computer_use", "arguments": {"action": "mouse_move", "coordinate": [111, 222]}}
</tool_call>
<tool_call>
{"name": "computer_use", "arguments": {"action": "left_click_drag", "coordinate": [333, 444]}}
</tool_call>
<tool_call>
{"name": "computer_use", "arguments": {"action": "press_click", "keys": ["ctrl"], "click_type": "left_click", "coordinate": [555, 666]}}
</tool_call>"""

        step = parse_raw_output(raw)

        assert len(step.actions) == 3
        assert step.actions[0].type == ActionType.MOUSE_MOVE
        assert step.actions[0].argument == "111, 222"
        assert step.actions[1].type == ActionType.LEFT_CLICK_DRAG
        assert step.actions[1].argument == "333, 444"
        assert step.actions[2].type == ActionType.PRESS_CLICK

        press_click_payload = json.loads(step.actions[2].argument)
        assert press_click_payload["keys"] == ["ctrl"]
        assert press_click_payload["click_type"] == "left_click"
        assert press_click_payload["coordinate"] == [555, 666]

    def test_qwen3_mode_fallbacks_to_legacy_when_legacy_tags_present(self):
        raw = "<|think_start|>Legacy reasoning<|think_end|>\n<|action_start|>click(7, 8)<|action_end|>"
        step = parse_raw_output(raw, parser_mode="qwen3")

        assert step.reason == "Legacy reasoning"
        assert len(step.actions) == 1
        assert step.actions[0].type == ActionType.CLICK
        assert step.actions[0].argument == "7, 8"


class TestParserMode:
    def test_legacy_mode(self):
        raw = "<|think_start|>Click<|think_end|>\n<|action_start|>click(100, 200)<|action_end|>"
        step = parse_raw_output(raw, parser_mode="legacy")

        assert step.reason == "Click"
        assert len(step.actions) == 1
        assert step.actions[0].type == ActionType.CLICK

    def test_auto_mode_uses_qwen3_when_tool_call_exists(self):
        raw = """Action: Click button.
<tool_call>
{"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [500, 600]}}
</tool_call>"""
        step = parse_raw_output(raw, parser_mode="auto")

        assert len(step.actions) == 1
        assert step.actions[0].type == ActionType.CLICK
        assert step.actions[0].argument == "500, 600"

    def test_auto_mode_falls_back_to_legacy(self):
        raw = "<|think_start|>Click<|think_end|>\n<|action_start|>click(500, 300)<|action_end|>"
        step = parse_raw_output(raw, parser_mode="auto")

        assert len(step.actions) == 1
        assert step.actions[0].type == ActionType.CLICK

    def test_auto_mode_does_not_early_return_on_bad_tool_call_reason_only(self):
        raw = """Action: bad tool call.
<tool_call>
{not-json}
</tool_call>
<|think_start|>Legacy fallback<|think_end|>
<|action_start|>click(9, 10)<|action_end|>"""
        step = parse_raw_output(raw, parser_mode="auto")

        assert step.reason == "Legacy fallback"
        assert len(step.actions) == 1
        assert step.actions[0].type == ActionType.CLICK
        assert step.actions[0].argument == "9, 10"

    def test_invalid_parser_mode_raises(self):
        with pytest.raises(ValueError, match="Unsupported parser_mode"):
            parse_raw_output("Action: click", parser_mode="invalid")  # type: ignore[arg-type]


class TestLegacyHelpers:
    def test_split_actions_with_nested_parentheses(self):
        result = _split_actions("type(func(a, b)) & click(100, 200)")
        assert result == ["type(func(a, b))", "click(100, 200)"]

    def test_parse_legacy_scroll_with_count(self):
        action = _parse_action("scroll(500, 300, down, 3)")

        assert action is not None
        assert action.type == ActionType.SCROLL
        assert action.argument == "500,300,down"
        assert action.count == 3

    def test_parse_legacy_type_preserves_spaces(self):
        action = _parse_action("type( hello world )")

        assert action is not None
        assert action.type == ActionType.TYPE
        assert action.argument == " hello world "


class TestStepType:
    def test_returns_step_instance(self):
        raw = """Action: click.
<tool_call>
{"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [1, 2]}}
</tool_call>"""
        step = parse_raw_output(raw)

        assert isinstance(step, Step)
