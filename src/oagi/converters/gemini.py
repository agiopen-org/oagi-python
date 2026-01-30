# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Gemini action converter.

This module provides the GeminiActionConverter for converting Gemini CUA
actions to pyautogui command strings.
"""

from typing import Any

from .base import BaseActionConverter
from .models import GeminiAction

# Gemini uses 0-1000 coordinate space
GEMINI_COORD_SIZE = 1000


class GeminiActionConverter(BaseActionConverter[GeminiAction]):
    """Convert Gemini CUA actions to pyautogui command strings.

    This converter handles:
    1. Coordinate scaling from 0-1000 space to sandbox dimensions (1920x1080)
    2. Action format conversion from Gemini format to pyautogui strings
    3. High-level actions like navigate, search, go_back
    4. Key name normalization for hotkey combinations

    The output can be converted to runtime API steps via action_string_to_step().
    """

    @property
    def coord_width(self) -> int:
        return GEMINI_COORD_SIZE

    @property
    def coord_height(self) -> int:
        return GEMINI_COORD_SIZE

    def _parse_gemini_hotkey(self, keys_str: str) -> list[str]:
        """Parse Gemini hotkey string into list of normalized keys."""
        keys_str = keys_str.replace("-", "+")
        keys = [self.normalize_key(k) for k in keys_str.split("+") if k.strip()]
        return keys

    def _convert_single_action(self, action: GeminiAction) -> list[str]:
        """Convert a single Gemini action to pyautogui command string(s)."""
        action_type = action.action_type.lower()
        hotkey_interval = self.config.hotkey_interval

        if action_type == "open_web_browser":
            return []  # No-op

        if action_type == "click_at":
            if action.x is None or action.y is None:
                raise ValueError("x and y are required for click_at")
            x, y = self.scale_coordinate(action.x, action.y)
            self._last_x, self._last_y = x, y
            return [f"pyautogui.click(x={x}, y={y})"]

        if action_type == "hover_at":
            if action.x is None or action.y is None:
                raise ValueError("x and y are required for hover_at")
            x, y = self.scale_coordinate(action.x, action.y)
            self._last_x, self._last_y = x, y
            return [f"pyautogui.moveTo({x}, {y})"]

        if action_type == "type_text_at":
            if action.x is None or action.y is None:
                raise ValueError("x and y are required for type_text_at")
            if action.text is None:
                raise ValueError("text is required for type_text_at")

            x, y = self.scale_coordinate(action.x, action.y)
            self._last_x, self._last_y = x, y

            commands = [f"pyautogui.click(x={x}, y={y})"]

            if action.clear_before_typing:
                commands.append(
                    f"pyautogui.hotkey('ctrl', 'a', interval={hotkey_interval})"
                )
                commands.append("pyautogui.press('delete')")

            text = action.text.replace("\\", "\\\\").replace("'", "\\'")
            commands.append(f"pyautogui.typewrite('{text}')")

            if action.press_enter:
                commands.append("pyautogui.press('enter')")

            return commands

        if action_type == "scroll_document":
            direction = (action.direction or "down").strip().lower()

            if direction == "down":
                return ["pyautogui.press('pagedown')"]
            elif direction == "up":
                return ["pyautogui.press('pageup')"]
            elif direction == "left":
                return ["pyautogui.press('left')"]
            elif direction == "right":
                return ["pyautogui.press('right')"]
            else:
                raise ValueError(f"Invalid scroll direction: {direction}")

        if action_type == "scroll_at":
            if action.x is None or action.y is None:
                raise ValueError("x and y are required for scroll_at")

            x, y = self.scale_coordinate(action.x, action.y)
            direction = (action.direction or "down").strip().lower()

            amount = self.config.scroll_amount
            if action.magnitude is not None:
                amount = max(1, action.magnitude // 100)

            if direction == "up":
                scroll_val = amount
            elif direction == "down":
                scroll_val = -amount
            else:
                self._log_debug(
                    f"Unsupported scroll direction '{direction}', defaulting to down"
                )
                scroll_val = -amount

            return [
                f"pyautogui.moveTo({x}, {y})",
                f"pyautogui.scroll({scroll_val})",
            ]

        if action_type == "wait_5_seconds":
            return ["WAIT(5)"]

        if action_type == "go_back":
            return [f"pyautogui.hotkey('alt', 'left', interval={hotkey_interval})"]

        if action_type == "go_forward":
            return [f"pyautogui.hotkey('alt', 'right', interval={hotkey_interval})"]

        if action_type == "search":
            return [
                f"pyautogui.hotkey('ctrl', 'l', interval={hotkey_interval})",
                "pyautogui.typewrite('https://www.google.com')",
                "pyautogui.press('enter')",
            ]

        if action_type == "navigate":
            if action.url is None:
                raise ValueError("url is required for navigate action")
            url = action.url
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            url = url.replace("'", "\\'")
            return [
                f"pyautogui.hotkey('ctrl', 'l', interval={hotkey_interval})",
                f"pyautogui.hotkey('ctrl', 'a', interval={hotkey_interval})",
                f"pyautogui.typewrite('{url}')",
                "pyautogui.press('enter')",
            ]

        if action_type == "key_combination":
            if action.keys is None:
                raise ValueError("keys is required for key_combination action")
            keys = self._parse_gemini_hotkey(action.keys)
            if not keys:
                raise ValueError(f"Invalid key combination: {action.keys}")
            keys_str = ", ".join(repr(k) for k in keys)
            return [f"pyautogui.hotkey({keys_str}, interval={hotkey_interval})"]

        if action_type == "drag_and_drop":
            if action.x is None or action.y is None:
                raise ValueError(
                    "x and y (start position) are required for drag_and_drop"
                )
            if action.destination_x is None or action.destination_y is None:
                raise ValueError(
                    "destination_x and destination_y are required for drag_and_drop"
                )

            sx, sy = self.scale_coordinate(action.x, action.y)
            ex, ey = self.scale_coordinate(action.destination_x, action.destination_y)
            self._last_x, self._last_y = ex, ey

            return [
                f"pyautogui.moveTo({sx}, {sy})",
                f"pyautogui.dragTo({ex}, {ey}, duration={self.config.drag_duration})",
            ]

        self._log_debug(f"Unknown Gemini action type: {action_type}")
        return []

    def serialize_actions(self, actions: list[GeminiAction]) -> list[dict[str, Any]]:
        """Serialize Gemini actions for trajectory logging."""
        serialized = []
        for action in actions or []:
            serialized.append(
                {
                    "type": action.action_type,
                    "x": action.x,
                    "y": action.y,
                    "text": action.text,
                    "press_enter": action.press_enter,
                    "clear_before_typing": action.clear_before_typing,
                    "direction": action.direction,
                    "magnitude": action.magnitude,
                    "destination_x": action.destination_x,
                    "destination_y": action.destination_y,
                    "keys": action.keys,
                    "url": action.url,
                }
            )
        return serialized
