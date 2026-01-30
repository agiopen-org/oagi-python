# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Action converters for multi-model VLM support.

This module provides converters for different VLM models:
- OAGI: Native OAGI actions (0-1000 normalized coordinates)
- Claude: Claude CUA actions (XGA 1024x768 coordinates)
- Qwen3: Qwen3-VL actions (0-999 normalized coordinates)
- Gemini: Gemini CUA actions (0-1000 normalized coordinates)

All converters output pyautogui command strings that can be:
1. Executed locally via PyautoguiActionHandler
2. Sent to remote sandbox via runtime API (using action_string_to_step())

Example usage:
    from oagi.converters import ClaudeActionConverter, ClaudeAction, ConverterConfig

    # Configure for 1920x1080 sandbox
    config = ConverterConfig(sandbox_width=1920, sandbox_height=1080)
    converter = ClaudeActionConverter(config=config)

    # Convert Claude actions to pyautogui strings
    actions = [ClaudeAction(action_type="left_click", coordinate=(512, 384))]
    pyautogui_commands = converter(actions)

    # Convert to runtime API steps
    for cmd, is_last in pyautogui_commands:
        step = converter.action_string_to_step(cmd)
        # Execute step via runtime API...
"""

from oagi.converters.base import BaseActionConverter, ConverterConfig
from oagi.converters.claude import ClaudeActionConverter
from oagi.converters.gemini import GeminiActionConverter
from oagi.converters.models import ClaudeAction, GeminiAction, Qwen3Action
from oagi.converters.oagi import OagiActionConverter
from oagi.converters.qwen3 import Qwen3ActionConverter

__all__ = [
    # Base
    "BaseActionConverter",
    "ConverterConfig",
    # Converters
    "OagiActionConverter",
    "ClaudeActionConverter",
    "Qwen3ActionConverter",
    "GeminiActionConverter",
    # Action models
    "ClaudeAction",
    "Qwen3Action",
    "GeminiAction",
]
