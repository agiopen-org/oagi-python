# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Claude action converter.

This module provides the ClaudeActionConverter for converting Claude CUA
(Computer Use Agent) actions to pyautogui command strings.
"""

from typing import Any

from .base import BaseActionConverter
from .models import ClaudeAction

# Claude uses XGA resolution (1024x768) for coordinate space
XGA_WIDTH = 1024
XGA_HEIGHT = 768


class ClaudeActionConverter(BaseActionConverter[ClaudeAction]):
    """Convert Claude CUA actions to pyautogui command strings.

    This converter handles:
    1. Coordinate scaling from XGA (1024x768) to sandbox dimensions (1920x1080)
    2. Action format conversion from Claude format to pyautogui strings
    3. Key name normalization for hotkey combinations

    The output can be converted to runtime API steps via action_string_to_step().
    """

    @property
    def coord_width(self) -> int:
        return XGA_WIDTH

    @property
    def coord_height(self) -> int:
        return XGA_HEIGHT

    def _parse_claude_hotkey(self, text: str) -> list[str]:
        """Parse Claude hotkey string into list of normalized keys.

        Claude uses "-" or "+" as separators.
        """
        text = text.replace("-", "+")
        keys = [self.normalize_key(k) for k in text.split("+") if k.strip()]
        return keys

    def _get_coords_or_last(self, action: ClaudeAction) -> tuple[int, int]:
        """Get scaled coordinates from action or fall back to last position."""
        if action.coordinate is not None:
            x, y = self.scale_coordinate(*action.coordinate)
            self._last_x, self._last_y = x, y
            return x, y
        elif self._last_x is not None and self._last_y is not None:
            return self._last_x, self._last_y
        else:
            return self._get_last_or_center()

    def _convert_single_action(self, action: ClaudeAction) -> list[str]:
        """Convert a single Claude action to pyautogui command string(s)."""
        action_type = action.action_type.lower()

        if action_type == "screenshot":
            return []  # No-op

        if action_type == "mouse_move":
            if action.coordinate is None:
                raise ValueError("coordinate is required for mouse_move")
            x, y = self.scale_coordinate(*action.coordinate)
            self._last_x, self._last_y = x, y
            return [f"pyautogui.moveTo({x}, {y})"]

        if action_type == "left_click":
            x, y = self._get_coords_or_last(action)
            return [f"pyautogui.click(x={x}, y={y})"]

        if action_type == "double_click":
            x, y = self._get_coords_or_last(action)
            return [f"pyautogui.doubleClick(x={x}, y={y})"]

        if action_type == "triple_click":
            x, y = self._get_coords_or_last(action)
            return [f"pyautogui.tripleClick(x={x}, y={y})"]

        if action_type == "right_click":
            x, y = self._get_coords_or_last(action)
            return [f"pyautogui.rightClick(x={x}, y={y})"]

        if action_type == "middle_click":
            x, y = self._get_coords_or_last(action)
            return [f"pyautogui.click(x={x}, y={y}, button='middle')"]

        if action_type == "left_click_drag":
            # Start from start_coordinate or last position
            if action.start_coordinate is not None:
                sx, sy = self.scale_coordinate(*action.start_coordinate)
            elif self._last_x is not None and self._last_y is not None:
                sx, sy = self._last_x, self._last_y
            else:
                sx, sy = self._get_last_or_center()

            # End at coordinate
            if action.coordinate is None:
                raise ValueError(
                    "coordinate (end position) is required for left_click_drag"
                )
            ex, ey = self.scale_coordinate(*action.coordinate)
            self._last_x, self._last_y = ex, ey

            return [
                f"pyautogui.moveTo({sx}, {sy})",
                f"pyautogui.dragTo({ex}, {ey}, duration={self.config.drag_duration})",
            ]

        if action_type == "type":
            if action.text is None:
                raise ValueError("text is required for type action")
            text = action.text.replace("\\", "\\\\").replace("'", "\\'")
            return [f"pyautogui.typewrite('{text}')"]

        if action_type == "key":
            if action.text is None:
                raise ValueError("text is required for key action")
            keys = self._parse_claude_hotkey(action.text)
            if not keys:
                raise ValueError(f"Invalid key combination: {action.text}")
            keys_str = ", ".join(repr(k) for k in keys)
            return [
                f"pyautogui.hotkey({keys_str}, interval={self.config.hotkey_interval})"
            ]

        if action_type == "scroll":
            if action.coordinate is None:
                raise ValueError("coordinate is required for scroll action")
            x, y = self.scale_coordinate(*action.coordinate)

            direction = (action.scroll_direction or "down").strip().lower()
            amount = (
                action.scroll_amount
                if action.scroll_amount is not None
                else self.config.scroll_amount
            )

            if direction == "up":
                scroll_val = amount
            elif direction == "down":
                scroll_val = -amount
            else:
                raise ValueError(f"Invalid scroll direction: {direction}")

            return [
                f"pyautogui.moveTo({x}, {y})",
                f"pyautogui.scroll({scroll_val})",
            ]

        if action_type == "wait":
            duration = (
                action.duration
                if action.duration is not None
                else self.config.wait_duration
            )
            return [f"WAIT({duration})"]

        if action_type == "cursor_position":
            return []  # No-op

        self._log_debug(f"Unknown Claude action type: {action_type}")
        return []

    def serialize_actions(self, actions: list[ClaudeAction]) -> list[dict[str, Any]]:
        """Serialize Claude actions for trajectory logging."""
        serialized = []
        for action in actions or []:
            serialized.append(
                {
                    "type": action.action_type,
                    "coordinate": list(action.coordinate)
                    if action.coordinate
                    else None,
                    "start_coordinate": list(action.start_coordinate)
                    if action.start_coordinate
                    else None,
                    "text": action.text,
                    "scroll_direction": action.scroll_direction,
                    "scroll_amount": action.scroll_amount,
                    "duration": action.duration,
                }
            )
        return serialized
