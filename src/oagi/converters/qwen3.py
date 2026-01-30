# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Qwen3 action converter.

This module provides the Qwen3ActionConverter for converting Qwen3-VL
actions to pyautogui command strings.
"""

from typing import Any

from .base import BaseActionConverter, ConverterConfig
from .models import Qwen3Action

# Qwen3 uses normalized 0-999 coordinate space
QWEN3_COORD_SIZE = 999


class Qwen3ActionConverter(BaseActionConverter[Qwen3Action]):
    """Convert Qwen3 CUA actions to pyautogui command strings.

    This converter handles:
    1. Coordinate scaling from 0-999 space to sandbox dimensions (1920x1080)
    2. Action format conversion from Qwen3 format to pyautogui strings
    3. Key name normalization for hotkey combinations
    4. Cursor position tracking for scroll and drag actions

    The output can be converted to runtime API steps via action_string_to_step().
    """

    def __init__(
        self,
        *,
        config: ConverterConfig | None = None,
        logger: Any | None = None,
    ):
        """Initialize the Qwen3 converter.

        Qwen3 starts with cursor at screen center by default.
        """
        super().__init__(config=config, logger=logger)
        # Qwen3 starts cursor at center
        self._last_x = self.config.sandbox_width // 2
        self._last_y = self.config.sandbox_height // 2

    @property
    def coord_width(self) -> int:
        return QWEN3_COORD_SIZE

    @property
    def coord_height(self) -> int:
        return QWEN3_COORD_SIZE

    def _get_coords_from_action(self, action: Qwen3Action) -> tuple[int, int]:
        """Extract and scale coordinates from action, falling back to last position."""
        if action.coordinate is not None and len(action.coordinate) >= 2:
            x, y = action.coordinate[:2]
            scaled_x, scaled_y = self.scale_coordinate(int(x), int(y))
            self._last_x, self._last_y = scaled_x, scaled_y
            return scaled_x, scaled_y
        else:
            return self._last_x, self._last_y

    def _convert_single_action(self, action: Qwen3Action) -> list[str]:
        """Convert a single Qwen3 action to pyautogui command string(s)."""
        action_type = action.action_type.lower()

        if action_type == "mouse_move":
            x, y = self._get_coords_from_action(action)
            return [f"pyautogui.moveTo({x}, {y})"]

        if action_type == "left_click":
            x, y = self._get_coords_from_action(action)
            return [f"pyautogui.click(x={x}, y={y})"]

        if action_type == "double_click":
            x, y = self._get_coords_from_action(action)
            return [f"pyautogui.doubleClick(x={x}, y={y})"]

        if action_type == "triple_click":
            x, y = self._get_coords_from_action(action)
            return [f"pyautogui.tripleClick(x={x}, y={y})"]

        if action_type == "right_click":
            x, y = self._get_coords_from_action(action)
            return [f"pyautogui.rightClick(x={x}, y={y})"]

        if action_type == "middle_click":
            x, y = self._get_coords_from_action(action)
            return [f"pyautogui.click(x={x}, y={y}, button='middle')"]

        if action_type == "left_click_drag":
            sx, sy = self._last_x, self._last_y

            if action.coordinate is None or len(action.coordinate) < 2:
                raise ValueError(
                    "coordinate (end position) is required for left_click_drag"
                )

            ex, ey = self.scale_coordinate(
                int(action.coordinate[0]), int(action.coordinate[1])
            )
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
            if action.keys is None or len(action.keys) == 0:
                raise ValueError("keys array is required for key action")

            keys = [self.normalize_key(k) for k in action.keys]
            keys = [k for k in keys if k]

            if not keys:
                raise ValueError(f"Invalid key combination: {action.keys}")

            keys_str = ", ".join(repr(k) for k in keys)
            return [
                f"pyautogui.hotkey({keys_str}, interval={self.config.hotkey_interval})"
            ]

        if action_type in ("scroll", "hscroll"):
            x, y = self._get_coords_from_action(action)

            pixels = action.pixels if action.pixels is not None else 0
            if pixels >= 0:
                scroll_val = self.config.scroll_amount
            else:
                scroll_val = -self.config.scroll_amount

            return [
                f"pyautogui.moveTo({x}, {y})",
                f"pyautogui.scroll({scroll_val})",
            ]

        if action_type == "wait":
            duration = (
                action.time if action.time is not None else self.config.wait_duration
            )
            return [f"WAIT({duration})"]

        if action_type == "terminate":
            status = action.status or "success"
            self._log_info(f"Task terminated with status: {status}")
            return ["DONE"]

        if action_type == "answer":
            answer_text = action.text or ""
            self._log_info(f"Model answer: {answer_text}")
            return []  # No-op

        self._log_debug(f"Unknown Qwen3 action type: {action_type}")
        return []

    def serialize_actions(self, actions: list[Qwen3Action]) -> list[dict[str, Any]]:
        """Serialize Qwen3 actions for trajectory logging."""
        serialized = []
        for action in actions or []:
            serialized.append(
                {
                    "type": action.action_type,
                    "coordinate": list(action.coordinate)
                    if action.coordinate
                    else None,
                    "text": action.text,
                    "keys": action.keys,
                    "pixels": action.pixels,
                    "time": action.time,
                    "status": action.status,
                }
            )
        return serialized

    def update_cursor(self, x: int, y: int) -> None:
        """Update the cursor position after action execution."""
        self._last_x = x
        self._last_y = y

    def get_cursor(self) -> tuple[int, int]:
        """Get current cursor position in sandbox coordinates."""
        return self._last_x, self._last_y
