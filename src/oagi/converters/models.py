# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Action dataclasses for model-specific action converters.

This module provides dataclass definitions for actions from different VLM models:
- ClaudeAction: Claude CUA actions (XGA 1024x768 coordinates)
- Qwen3Action: Qwen3-VL actions (0-999 normalized coordinates)
- GeminiAction: Gemini actions (0-1000 normalized coordinates)

Note: OAGI actions use the existing oagi.types.Action model.
"""

from dataclasses import dataclass


@dataclass
class ClaudeAction:
    """Represents a Claude computer use action.

    Claude uses XGA coordinates (1024x768) for coordinate actions.

    Attributes:
        action_type: The type of action (e.g., "left_click", "type", "key")
        coordinate: XGA coordinates (x, y) where x in [0,1024] and y in [0,768]
        text: Text content for type or key actions
        scroll_direction: Direction for scroll ("up" or "down")
        scroll_amount: Amount to scroll (optional, uses default if not specified)
        duration: Duration in milliseconds for wait actions
        start_coordinate: Starting coordinate for drag operations
    """

    action_type: str
    coordinate: tuple[int, int] | None = None
    text: str | None = None
    scroll_direction: str | None = None
    scroll_amount: int | None = None
    duration: int | None = None
    start_coordinate: tuple[int, int] | None = None


@dataclass
class Qwen3Action:
    """Represents a Qwen3 computer use action.

    Qwen3 uses normalized coordinates (0-999) for coordinate actions.

    Attributes:
        action_type: The type of action (e.g., "left_click", "type", "key")
        coordinate: Normalized coordinates (x, y) where both x and y in [0,999]
        text: Text content for type and answer actions
        keys: List of key names for key/hotkey actions
        pixels: Pixel amount for scroll actions
        time: Duration in seconds for wait actions
        status: Status string for terminate actions ("success" or "failure")
    """

    action_type: str
    coordinate: tuple[int, int] | None = None
    text: str | None = None
    keys: list[str] | None = None
    pixels: int | None = None
    time: float | None = None
    status: str | None = None


@dataclass
class GeminiAction:
    """Represents a Gemini computer use action.

    Gemini uses normalized coordinates (0-1000) for coordinate actions.

    Attributes:
        action_type: The type of action (e.g., "click_at", "type_text_at", "scroll_at")
        x: X coordinate (0-1000)
        y: Y coordinate (0-1000)
        text: Text content for typing actions
        press_enter: Whether to press Enter after typing
        clear_before_typing: Whether to clear existing text before typing
        direction: Scroll direction ("up", "down", "left", "right")
        magnitude: Scroll magnitude in pixels
        destination_x: Destination X coordinate for drag operations
        destination_y: Destination Y coordinate for drag operations
        keys: Key combination string for key actions (e.g., "ctrl+c")
        url: URL for navigation actions
    """

    action_type: str
    x: int | None = None
    y: int | None = None
    text: str | None = None
    press_enter: bool | None = None
    clear_before_typing: bool | None = None
    direction: str | None = None
    magnitude: int | None = None
    destination_x: int | None = None
    destination_y: int | None = None
    keys: str | None = None
    url: str | None = None
