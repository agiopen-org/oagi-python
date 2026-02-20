# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Literal

PromptMode = Literal["qwen3", "legacy"]

_LEGACY_INSTRUCTION_TEMPLATE = """You are a Desktop Agent completing computer use tasks from a user instruction.

Every step, you will look at the screenshot and output the desired actions in a format as:

<|think_start|> brief description of your intent and reasoning <|think_end|>
<|action_start|> one of the allowed actions as below <|action_end|>

In the action field, you have the following action formats:
1. click(x, y) # left-click at the position (x, y), where x and y are integers normalized between 0 and 1000
2. left_double(x, y) # left-double-click at the position (x, y), where x and y are integers normalized between 0 and 1000
3. left_triple(x, y) # left-triple-click at the position (x, y), where x and y are integers normalized between 0 and 1000
4. right_single(x, y) # right-click at the position (x, y), where x and y are integers normalized between 0 and 1000
5. drag(x1, y1, x2, y2) # drag the mouse from (x1, y1) to (x2, y2) to select or move contents, where x1, y1, x2, y2 are integers normalized between 0 and 1000
6. hotkey(key, c) # press the key for c times
7. type(text) # type a text string on the keyboard
8. scroll(x, y, direction, c) # scroll the mouse at position (x, y) in the direction of up or down for c times, where x and y are integers normalized between 0 and 1000
9. wait() # wait for a while
10. finish() # indicate the task is finished
11. fail() # indicate the task is infeasible

Directly output the text beginning with <|think_start|>, no additional text is needed for this scenario.

The user instruction is:
{instruction}
"""


_QWEN3_INSTRUCTION_TEMPLATE = """Please generate the next move according to the UI screenshot, instruction and previous actions.

Instruction: {instruction}

Previous actions:
{previous_actions}
"""


def build_prompt(
    task_description: str,
    previous_actions: str | None = None,
    prompt_mode: PromptMode = "qwen3",
) -> str:
    """Build the instruction prompt for the selected model style.

    Args:
        task_description: Task description to include in the prompt.
        previous_actions: Historical action summary text.
        prompt_mode: Prompt template mode ("qwen3" or "legacy").

    Returns:
        Formatted prompt string.
    """
    if prompt_mode == "legacy":
        return _LEGACY_INSTRUCTION_TEMPLATE.format(instruction=task_description)

    if prompt_mode == "qwen3":
        return _QWEN3_INSTRUCTION_TEMPLATE.format(
            instruction=task_description,
            previous_actions=previous_actions or "None",
        )

    raise ValueError(
        f"Unsupported prompt_mode: {prompt_mode}. Expected 'qwen3' or 'legacy'."
    )
