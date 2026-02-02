# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Action converters for VLM support.

This module provides the base class and OAGI implementation for action converters.
Third parties can inherit from BaseActionConverter to create custom converters.

Example usage:
    from oagi.converters import OagiActionConverter, ConverterConfig

    # Configure for 1920x1080 sandbox
    config = ConverterConfig(sandbox_width=1920, sandbox_height=1080)
    converter = OagiActionConverter(config=config)

    # Convert OAGI actions to pyautogui strings
    result = converter(actions)  # list[tuple[str, bool]]

    # Convert to runtime API steps
    for cmd, is_last in result:
        step = converter.action_string_to_step(cmd)
        # Execute step via runtime API...

Creating custom converters:
    from oagi.converters import BaseActionConverter, ConverterConfig

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

from oagi.converters.base import BaseActionConverter, ConverterConfig
from oagi.converters.oagi import OagiActionConverter

__all__ = [
    "BaseActionConverter",
    "ConverterConfig",
    "OagiActionConverter",
]
