# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import re

from ..types.models.action import Action, ActionType
from ..types.models.step import Step


def parse_raw_output(raw_output: str) -> Step:
    """Parse raw LLM output into structured Step format.

    Expected format:
    <|think_start|> reasoning text <|think_end|>
    <|action_start|> action1(args) & action2(args) & ... <|action_end|>

    Args:
        raw_output: Raw text output from the LLM

    Returns:
        Step object with parsed reasoning and actions
    """
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
                if parsed_action.type == ActionType.FINISH:
                    stop = True

    return Step(reason=reason, actions=actions, stop=stop)


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

    Args:
        action_text: String representation of a single action

    Returns:
        Action object or None if parsing fails
    """
    # Match action format: action_type(arguments)
    match = re.match(r"(\w+)\((.*)\)", action_text.strip())
    if not match:
        return None

    action_type = match.group(1).lower()
    arguments = match.group(2).strip()

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
