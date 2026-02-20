# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import json
import re
from typing import Any, Literal

from ..types.models.action import Action, ActionType
from ..types.models.step import Step


ParserMode = Literal["qwen3", "legacy", "auto"]


def parse_raw_output(
    raw_output: str,
    parser_mode: ParserMode = "qwen3",
) -> Step:
    """Parse raw LLM output into a structured Step.

    Args:
        raw_output: Raw text output from the LLM.
        parser_mode:
            - "qwen3": Parse `<tool_call>{...}</tool_call>` JSON format.
            - "legacy": Parse `<|think_start|>...<|action_start|>...` format.
            - "auto": Try qwen3 first when tool-call tags are present, otherwise legacy.
    """
    if parser_mode == "qwen3":
        return _parse_qwen3_output(raw_output)
    if parser_mode == "legacy":
        return _parse_legacy_output(raw_output)
    if parser_mode == "auto":
        if "<tool_call>" in raw_output:
            qwen3_step = _parse_qwen3_output(raw_output)
            if qwen3_step.actions or qwen3_step.reason:
                return qwen3_step
        if "<|action_start|>" in raw_output or "<|think_start|>" in raw_output:
            return _parse_legacy_output(raw_output)
        qwen3_step = _parse_qwen3_output(raw_output)
        if qwen3_step.actions or qwen3_step.reason:
            return qwen3_step
        return _parse_legacy_output(raw_output)

    raise ValueError(
        f"Unsupported parser_mode: {parser_mode}. Expected one of 'qwen3', 'legacy', 'auto'."
    )


def _parse_legacy_output(raw_output: str) -> Step:
    """Parse legacy tag-based output format."""
    # Extract reasoning/thinking
    think_pattern = r"<\|think_start\|>(.*?)<\|think_end\|>"
    think_match = re.search(think_pattern, raw_output, re.DOTALL)
    reason = think_match.group(1).strip() if think_match else ""

    # Extract action block
    action_pattern = r"<\|action_start\|>(.*?)<\|action_end\|>"
    action_match = re.search(action_pattern, raw_output, re.DOTALL)

    actions: list[Action] = []
    stop = False

    if action_match:
        action_block = action_match.group(1).strip()
        action_texts = _split_actions(action_block)

        for action_text in action_texts:
            parsed_action = _parse_action(action_text.strip())
            if parsed_action:
                actions.append(parsed_action)
                if parsed_action.type in (ActionType.FINISH, ActionType.FAIL):
                    stop = True

    return Step(reason=reason, actions=actions, stop=stop)


def _parse_qwen3_output(raw_output: str) -> Step:
    """Parse Qwen3-VL output format.

    Expected blocks:
    - Optional `<think>...</think>`
    - Optional `Action: ...` summary line
    - One or more `<tool_call>{...}</tool_call>` JSON blocks
    """
    think_match = re.search(r"<think>(.*?)</think>", raw_output, re.DOTALL | re.IGNORECASE)
    reason = think_match.group(1).strip() if think_match else ""

    action_summary = _extract_action_summary(raw_output)
    if not reason and action_summary:
        reason = action_summary

    actions: list[Action] = []
    for tool_call_content in re.findall(
        r"<tool_call>\s*(.*?)\s*</tool_call>",
        raw_output,
        re.DOTALL | re.IGNORECASE,
    ):
        tool_call_obj = _parse_tool_call_json(tool_call_content)
        if tool_call_obj is None:
            continue
        parsed_action = _parse_qwen3_tool_call(tool_call_obj)
        if parsed_action is not None:
            actions.append(parsed_action)

    stop = any(action.type in (ActionType.FINISH, ActionType.FAIL) for action in actions)
    return Step(reason=reason, actions=actions, stop=stop)


def _extract_action_summary(raw_output: str) -> str:
    """Extract first `Action: ...` summary line from raw output."""
    match = re.search(r"^\s*Action\s*:\s*(.+)$", raw_output, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _parse_tool_call_json(tool_call_content: str) -> dict[str, Any] | None:
    """Parse tool-call JSON payload from `<tool_call>...</tool_call>` block."""
    candidate = _strip_code_fence(tool_call_content)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _parse_qwen3_tool_call(tool_call_obj: dict[str, Any]) -> Action | None:
    """Convert one Qwen3 tool-call object into Action."""
    name = str(tool_call_obj.get("name", "")).strip()
    if name and name != "computer_use":
        return None

    arguments = tool_call_obj.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return None
    if not isinstance(arguments, dict):
        return None

    action_name = str(arguments.get("action", "")).strip().lower()
    if not action_name:
        return None

    count = _coerce_positive_int(arguments.get("count"), default=1)

    if action_name == "key":
        keys = _extract_keys(arguments.get("keys"))
        if not keys:
            return None
        return Action(
            type=ActionType.HOTKEY,
            argument="+".join(keys),
            count=count,
        )

    if action_name == "type":
        text = arguments.get("text", "")
        return Action(type=ActionType.TYPE, argument=str(text), count=count)

    if action_name == "mouse_move":
        coords = _extract_coords(arguments.get("coordinate"))
        if coords is None:
            return None
        return Action(
            type=ActionType.MOUSE_MOVE,
            argument=f"{coords[0]}, {coords[1]}",
            count=count,
        )

    if action_name in {
        "left_click",
        "right_click",
        "double_click",
        "triple_click",
    }:
        coords = _extract_coords(arguments.get("coordinate"))
        if coords is None:
            return None
        mapped_type = {
            "left_click": ActionType.CLICK,
            "right_click": ActionType.RIGHT_SINGLE,
            "double_click": ActionType.LEFT_DOUBLE,
            "triple_click": ActionType.LEFT_TRIPLE,
        }[action_name]
        return Action(type=mapped_type, argument=f"{coords[0]}, {coords[1]}", count=count)

    if action_name == "left_click_drag":
        coords = _extract_coords(arguments.get("coordinate"))
        if coords is None:
            return None
        return Action(
            type=ActionType.LEFT_CLICK_DRAG,
            argument=f"{coords[0]}, {coords[1]}",
            count=count,
        )

    if action_name == "press_click":
        coords = _extract_coords(arguments.get("coordinate"))
        keys = _extract_keys(arguments.get("keys"))
        click_type = str(arguments.get("click_type", "")).strip().lower()
        if coords is None:
            return None
        if click_type not in {
            "left_click",
            "right_click",
            "double_click",
            "triple_click",
        }:
            return None
        press_click_argument = json.dumps(
            {
                "keys": keys,
                "click_type": click_type,
                "coordinate": [coords[0], coords[1]],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return Action(
            type=ActionType.PRESS_CLICK,
            argument=press_click_argument,
            count=count,
        )

    if action_name == "scroll":
        coords = _extract_coords(arguments.get("coordinate")) or (500, 500)
        direction, scroll_count = _parse_scroll_direction_and_count(arguments)
        return Action(
            type=ActionType.SCROLL,
            argument=f"{coords[0]}, {coords[1]}, {direction}",
            count=scroll_count,
        )

    if action_name == "wait":
        wait_time = _coerce_float(arguments.get("time"), default=1.0)
        return Action(type=ActionType.WAIT, argument=str(wait_time), count=1)

    if action_name == "terminate":
        status = str(arguments.get("status", "success")).strip().lower()
        terminal_type = ActionType.FAIL if status == "failure" else ActionType.FINISH
        return Action(type=terminal_type, argument="", count=1)

    return None


def _extract_keys(raw_keys: Any) -> list[str]:
    if isinstance(raw_keys, list):
        return [str(key).strip() for key in raw_keys if str(key).strip()]
    if isinstance(raw_keys, str):
        split_keys = re.split(r"[+,]", raw_keys)
        return [key.strip() for key in split_keys if key.strip()]
    return []


def _extract_coords(raw_coords: Any) -> tuple[int, int] | None:
    if not isinstance(raw_coords, list | tuple) or len(raw_coords) < 2:
        return None
    try:
        x = int(float(raw_coords[0]))
        y = int(float(raw_coords[1]))
    except (TypeError, ValueError):
        return None
    return x, y


def _coerce_positive_int(value: Any, default: int = 1) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 1)


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_scroll_direction_and_count(arguments: dict[str, Any]) -> tuple[str, int]:
    direction = str(arguments.get("direction", "")).strip().lower()
    raw_count = arguments.get("count", 1)

    if isinstance(raw_count, (int, float)):
        signed_count = int(raw_count)
    else:
        signed_count = 1

    if direction not in {"up", "down"}:
        direction = "down" if signed_count < 0 else "up"

    count = max(abs(signed_count), 1)
    return direction, count


def _split_actions(action_block: str) -> list[str]:
    """Split action block by & separator, but only when & is outside parentheses.

    Note: This parser does NOT handle '&' inside quoted strings.
    E.g., type("a&b") would incorrectly split. The LLM should avoid
    this pattern by using alternative escape sequences.

    Args:
        action_block: String containing one or more actions separated by &

    Returns:
        List of individual action strings
    """
    actions: list[str] = []
    current_action: list[str] = []
    paren_level = 0

    for char in action_block:
        if char == "(":
            paren_level += 1
            current_action.append(char)
        elif char == ")":
            paren_level -= 1
            current_action.append(char)
        elif char == "&" and paren_level == 0:
            action_str = "".join(current_action).strip()
            if action_str:
                actions.append(action_str)
            current_action = []
        else:
            current_action.append(char)

    # Add the last action
    action_str = "".join(current_action).strip()
    if action_str:
        actions.append(action_str)

    return actions


def _parse_action(action_text: str) -> Action | None:
    """Parse individual action text into Action object.

    Expected formats:
    - click(x, y) # left-click at position
    - left_double(x, y) # left-double-click at position
    - left_triple(x, y) # left-triple-click at position
    - right_single(x, y) # right-click at position
    - drag(x1, y1, x2, y2) # drag from (x1, y1) to (x2, y2)
    - hotkey(key, c) # press key c times
    - type(text) # type text string
    - scroll(x, y, direction, c) # scroll at position
    - wait() # wait for a while
    - finish() # indicate task is finished
    - fail() # indicate task is infeasible

    Args:
        action_text: String representation of a single action

    Returns:
        Action object or None if parsing fails
    """
    # Match action format: action_type(arguments)
    # re.DOTALL allows '.' to match newlines for multiline type() content
    match = re.match(r"(\w+)\((.*)\)", action_text.strip(), re.DOTALL)
    if not match:
        return None

    action_type = match.group(1).lower()
    # Do not trim TYPE payload to preserve meaningful leading/trailing spaces.
    raw_arguments = match.group(2)
    arguments = (
        raw_arguments if action_type == ActionType.TYPE.value else raw_arguments.strip()
    )

    # Parse count from arguments for actions that support it
    count = 1

    # Validate and map action type to enum
    try:
        action_enum = ActionType(action_type)
    except ValueError:
        return None

    # Parse specific action types and extract count where applicable
    match action_enum:
        case ActionType.HOTKEY:
            # hotkey(key, c) - press key c times
            args = arguments.rsplit(",", 1)
            if len(args) >= 2 and args[1].strip():
                key = args[0].strip()
                try:
                    count = int(args[1].strip())
                except ValueError:
                    count = 1
            else:
                key = arguments.strip()
                count = 1
            arguments = key

        case ActionType.SCROLL:
            # scroll(x, y, direction, c) - scroll at position
            args = arguments.split(",")
            if len(args) >= 4:
                x = args[0].strip()
                y = args[1].strip()
                direction = args[2].strip()
                try:
                    count = int(args[3].strip())
                except (ValueError, IndexError):
                    count = 1
                # Reconstruct arguments without count
                arguments = f"{x},{y},{direction}"

        case _:
            # For other actions, use default count of 1
            pass

    return Action(type=action_enum, argument=arguments, count=count)
