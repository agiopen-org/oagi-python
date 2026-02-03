# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""OAGI action converter.

This module provides the OagiActionConverter for converting OAGI actions
to pyautogui command strings for remote execution.
"""

from typing import Any

from ..handler.utils import (
    parse_click_coords,
    parse_drag_coords,
    parse_scroll_coords,
)
from ..types import Action, ActionType
from .base import BaseActionConverter

# OAGI uses normalized 0-1000 coordinate space
OAGI_COORD_SIZE = 1000


class OagiActionConverter(BaseActionConverter[Action]):
    """Convert OAGI actions to pyautogui command strings.

    This converter handles:
    1. Coordinate scaling from 0-1000 space to sandbox dimensions (1920x1080)
    2. Action format conversion from OAGI Action format to pyautogui strings
    3. Key name normalization for hotkey combinations

    The output can be converted to runtime API steps via action_string_to_step().
    """

    @property
    def coord_width(self) -> int:
        return OAGI_COORD_SIZE

    @property
    def coord_height(self) -> int:
        return OAGI_COORD_SIZE

    def __call__(self, actions: list[Action]) -> list[tuple[str, bool]]:
        """Convert OAGI actions to list of (action_string, is_last) tuples.

        Extends base implementation to handle action count and finish detection.
        """
        converted: list[tuple[str, bool]] = []
        failed: list[tuple[str, str]] = []
        has_finish = False

        if not actions:
            return converted

        for action in actions:
            # Check for duplicate finish() during iteration
            is_finish = action.type == ActionType.FINISH
            if is_finish:
                if has_finish:
                    raise ValueError(
                        "Duplicate finish() detected. "
                        "Only one finish() is allowed per action sequence."
                    )
                has_finish = True

            try:
                converted.extend(self._convert_action(action))
            except Exception as e:
                action_repr = f"{action.type.value}({action.argument})"
                self._log_error(f"Failed to convert action: {action_repr}, error: {e}")
                failed.append((action_repr, str(e)))

        if not converted and actions and failed:
            raise RuntimeError(
                f"All action conversions failed ({len(failed)}/{len(actions)}): {failed}"
            )
        return converted

    def _convert_action(self, action: Action) -> list[tuple[str, bool]]:
        """Convert action to list of (action_string, is_last_of_repeat) tuples.

        Handles action.count for repeat support.
        """
        count = action.count or 1
        out: list[tuple[str, bool]] = []
        single_actions = self._convert_single_action(action)

        # Repeat the actions count times
        for i in range(int(count)):
            is_last_repeat = i == int(count) - 1
            for j, action_str in enumerate(single_actions):
                is_last = is_last_repeat and (j == len(single_actions) - 1)
                out.append((action_str, is_last))

        return out

    def _convert_single_action(self, action: Action) -> list[str]:
        """Convert a single OAGI action to pyautogui command string(s)."""
        action_type = action.type.value
        argument = (action.argument or "").strip("()")

        drag_duration = self.config.drag_duration
        scroll_amount = self.config.scroll_amount
        wait_duration = self.config.wait_duration
        hotkey_interval = self.config.hotkey_interval
        strict = self.config.strict_coordinate_validation

        if action_type == ActionType.CLICK.value:
            x, y = parse_click_coords(argument, self._coord_scaler, strict=strict)
            return [f"pyautogui.click(x={x}, y={y})"]

        if action_type == ActionType.LEFT_DOUBLE.value:
            x, y = parse_click_coords(argument, self._coord_scaler, strict=strict)
            return [f"pyautogui.doubleClick(x={x}, y={y})"]

        if action_type == ActionType.LEFT_TRIPLE.value:
            x, y = parse_click_coords(argument, self._coord_scaler, strict=strict)
            return [f"pyautogui.tripleClick(x={x}, y={y})"]

        if action_type == ActionType.RIGHT_SINGLE.value:
            x, y = parse_click_coords(argument, self._coord_scaler, strict=strict)
            return [f"pyautogui.rightClick(x={x}, y={y})"]

        if action_type == ActionType.DRAG.value:
            sx, sy, ex, ey = parse_drag_coords(
                argument, self._coord_scaler, strict=strict
            )
            return [
                f"pyautogui.moveTo({sx}, {sy})",
                f"pyautogui.dragTo({ex}, {ey}, duration={drag_duration})",
            ]

        if action_type == ActionType.HOTKEY.value:
            keys = self.parse_hotkey(argument, validate=True)
            valid_keys = [k for k in keys if k]
            if not valid_keys:
                raise ValueError(
                    f"Invalid hotkey format: '{argument}'. "
                    "Expected key names like 'ctrl+c', 'alt+tab'"
                )
            # Check if this is a caps lock key press
            if len(valid_keys) == 1 and valid_keys[0] == "capslock":
                if self.caps_manager.should_use_system_capslock():
                    return [f"pyautogui.hotkey('capslock', interval={hotkey_interval})"]
                else:
                    self.caps_manager.toggle()
                    return []  # No pyautogui command for session mode
            else:
                keys_str = ", ".join(repr(k) for k in valid_keys)
                return [f"pyautogui.hotkey({keys_str}, interval={hotkey_interval})"]

        if action_type == ActionType.TYPE.value:
            text = argument.strip("\"'")
            text = self.caps_manager.transform_text(text)
            return [f"pyautogui.typewrite({text!r})"]

        if action_type == ActionType.SCROLL.value:
            x, y, direction = parse_scroll_coords(
                argument, self._coord_scaler, strict=strict
            )
            amount = scroll_amount if direction == "up" else -scroll_amount
            return [f"pyautogui.moveTo({x}, {y})", f"pyautogui.scroll({amount})"]

        if action_type == ActionType.WAIT.value:
            try:
                seconds = float(argument) if argument else wait_duration
            except ValueError:
                raise ValueError(
                    f"Invalid wait duration: '{argument}'. "
                    "Expected numeric value in seconds."
                )
            return [f"WAIT({seconds})"]

        if action_type == ActionType.FINISH.value:
            self._log_info("Task completion action -> DONE")
            return ["DONE"]

        if action_type == ActionType.CALL_USER.value:
            self._log_info("User intervention requested")
            return []

        raise ValueError(
            f"Unknown action type: '{action_type}'. "
            "Supported: click, left_double, left_triple, right_single, drag, "
            "hotkey, type, scroll, wait, finish, call_user"
        )

    def serialize_actions(self, actions: list[Action]) -> list[dict[str, Any]]:
        """Serialize OAGI actions for trajectory logging."""
        return [
            {
                "type": action.type.value,
                "argument": action.argument,
                "count": action.count,
            }
            for action in (actions or [])
        ]
