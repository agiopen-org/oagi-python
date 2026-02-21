# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Action converters for VLM support.

This module provides PyautoguiActionConvertor for converting OAGI actions
to pyautogui command strings, and BaseActionConverter for custom converters.

Example usage:
    from oagi.converters import PyautoguiActionConvertor

    import logging
    converter = PyautoguiActionConvertor(logger=logging.getLogger(__name__))

    # Convert OAGI actions to pyautogui strings
    result = converter(actions)  # list[tuple[str, bool]]

    # Convert to runtime API steps
    for cmd, is_last in result:
        step = converter.action_string_to_step(cmd)
        # Execute step via runtime API...

Creating custom converters:
    from oagi.converters import BaseActionConverter
    from oagi.handler.utils import PyautoguiConfig

    class MyActionConverter(BaseActionConverter[MyAction]):
        @property
        def coord_width(self) -> int:
            return 1000  # Your model's coordinate width

        @property
        def coord_height(self) -> int:
            return 1000  # Your model's coordinate height

        def _convert_single_action(self, action: MyAction) -> list[str]:
            # Convert action to pyautogui command strings
            ...

        def serialize_actions(self, actions: list[MyAction]) -> list[dict]:
            # Serialize actions for trajectory logging
            ...
"""

from .base import BaseActionConverter
from .pyautogui_action_converter import PyautoguiActionConvertor

__all__ = [
    "BaseActionConverter",
    "PyautoguiActionConvertor",
]
