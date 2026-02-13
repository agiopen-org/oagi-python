# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""PyAutoGUI action converter.

This module provides PyautoguiActionConvertor for converting OAGI actions
to pyautogui command strings for remote execution via the sandbox runtime API.
"""

import logging
import re
from typing import Any

from ..handler.capslock_manager import CapsLockManager
from ..handler.utils import PYAUTOGUI_VALID_KEYS, PyautoguiConfig, make_type_command
from ..types import ActionType

# Sandbox configuration constants
DEFAULT_SANDBOX_WIDTH = 1920
DEFAULT_SANDBOX_HEIGHT = 1080
MODEL_COORD_WIDTH = 1000
MODEL_COORD_HEIGHT = 1000

# Converter uses scroll_amount=2 (not PyautoguiConfig's platform-dependent default
# of 100 on Linux) because commands execute in the remote sandbox VM.
DEFAULT_CONVERTER_SCROLL_AMOUNT = 2


class PyautoguiActionConvertor:
    """Convert OAGI actions to pyautogui command strings.

    This class mirrors the structure of PyautoguiActionHandler but instead of
    executing actions directly, it converts them to pyautogui command strings
    that can be executed remotely via the runtime API.

    Aligned with PyautoguiActionHandler structure:
    - __call__: Iterate actions and call _convert_action for each
    - _convert_action: Handle action count and call _convert_single_action
    - _convert_single_action: Convert individual action to pyautogui string(s)
    - _denormalize_coords: Map model/image coords to sandbox coords
    - CapsLockManager: Handle caps lock state for text transformation

    Key differences from PyautoguiActionHandler:
    - Returns pyautogui command strings instead of executing them
    - Uses custom coordinate scaling for sandbox dimensions
    - Integrates with runtime API via action_string_to_step method

    Args:
        logger: Logger instance for error and debug logging
        config: PyautoguiConfig instance. If not provided, uses default config
            with scroll_amount=2 (overriding the platform-dependent default).
    """

    def __init__(
        self,
        *,
        logger: logging.Logger,
        config: PyautoguiConfig | None = None,
    ) -> None:
        self.logger = logger

        # Use provided config or create default with converter-specific scroll_amount
        self.pyautogui_config = config or PyautoguiConfig(
            scroll_amount=DEFAULT_CONVERTER_SCROLL_AMOUNT,
        )

        self.sandbox_width = self.pyautogui_config.sandbox_width
        self.sandbox_height = self.pyautogui_config.sandbox_height

        self.coord_scale_x = self.sandbox_width / MODEL_COORD_WIDTH
        self.coord_scale_y = self.sandbox_height / MODEL_COORD_HEIGHT

        # Initialize caps lock manager
        self.caps_manager = CapsLockManager(mode=self.pyautogui_config.capslock_mode)

    def __call__(self, oagi_actions: list[Any]) -> list[tuple[str, bool]]:
        """Convert OAGI actions to list of (action_string, is_last_of_repeat) tuples.

        Returns:
            List of tuples: [(action_string, is_last_of_repeat), ...]

        Raises:
            ValueError: If duplicate finish() actions or other format errors detected
            RuntimeError: If all action conversions failed
        """
        converted: list[tuple[str, bool]] = []
        failed: list[tuple] = []
        has_terminal = False

        if not oagi_actions:
            return converted

        for action in oagi_actions:
            # Check for duplicate finish()/fail() during iteration
            action_type = getattr(action, "type", None)
            is_terminal = hasattr(action_type, "value") and action_type.value in (
                ActionType.FINISH.value,
                ActionType.FAIL.value,
            )
            if is_terminal:
                if has_terminal:
                    raise ValueError(
                        "Duplicate finish()/fail() detected. "
                        "Only one finish() or fail() is allowed per action sequence."
                    )
                has_terminal = True

            try:
                converted.extend(self._convert_action(action))
            except Exception as e:
                # Extract action details for better error logging
                action_arg = getattr(action, "argument", "unknown")
                action_repr = f"{action_type.value if hasattr(action_type, 'value') else action_type}({action_arg})"
                self.logger.error(
                    f"Failed to convert action: {action_repr}, error: {e}"
                )
                failed.append((action_repr, str(e)))

        if not converted and oagi_actions:
            raise RuntimeError(
                f"All action conversions failed ({len(failed)}/{len(oagi_actions)}): {failed}"
            )
        return converted

    def _convert_action(self, action: Any) -> list[tuple[str, bool]]:
        """Convert action to list of (action_string, is_last_of_repeat) tuples.

        Args:
            action: OAGI action object

        Returns:
            List of tuples: [(action_string, is_last_of_repeat), ...]
            is_last_of_repeat indicates whether this is the last action in a count>1 sequence
        """
        if not hasattr(action, "type") or not hasattr(action, "argument"):
            raise ValueError("Action missing required attribute 'type' or 'argument'")
        count = getattr(action, "count", None) or 1
        out: list[tuple[str, bool]] = []
        single_actions = self._convert_single_action(action)

        # Repeat the actions count times
        for i in range(int(count)):
            is_last_repeat = i == int(count) - 1  # True only on last iteration
            for j, action_str in enumerate(single_actions):
                # Only mark the very last command of the very last repeat as is_last
                is_last = is_last_repeat and (j == len(single_actions) - 1)
                out.append((action_str, is_last))

        return out

    def _denormalize_coords(self, x: float, y: float) -> tuple[int, int]:
        """Convert normalized coordinates to actual sandbox screen coordinates.

        Args:
            x: Normalized x coordinate (must be in range [0, MODEL_COORD_WIDTH])
            y: Normalized y coordinate (must be in range [0, MODEL_COORD_HEIGHT])

        Returns:
            Tuple of (screen_x, screen_y) in valid screen bounds

        Raises:
            ValueError: If coordinates are outside the valid model coordinate range [0, 1000]
        """
        # Validate input coordinates are within model coordinate range
        # Model outputs coordinates normalized between 0 and 1000
        if x < 0 or x > MODEL_COORD_WIDTH:
            raise ValueError(
                f"x coordinate {x} out of valid range [0, {MODEL_COORD_WIDTH}]. "
                f"Coordinates must be normalized between 0 and {MODEL_COORD_WIDTH}."
            )
        if y < 0 or y > MODEL_COORD_HEIGHT:
            raise ValueError(
                f"y coordinate {y} out of valid range [0, {MODEL_COORD_HEIGHT}]. "
                f"Coordinates must be normalized between 0 and {MODEL_COORD_HEIGHT}."
            )

        scaled_x = round(x * self.coord_scale_x)
        scaled_y = round(y * self.coord_scale_y)

        # Clamp coordinates to ensure valid screen positions (handles edge case at exactly 1000)
        scaled_x = max(0, min(scaled_x, self.sandbox_width - 1))
        scaled_y = max(0, min(scaled_y, self.sandbox_height - 1))

        return scaled_x, scaled_y

    def _parse_click_coords(self, argument: str) -> tuple[int, int]:
        """Parse click coordinates from argument string.

        Args:
            argument: Coordinate string in format "x, y"

        Returns:
            Tuple of denormalized (x, y) coordinates

        Raises:
            ValueError: If coordinate format is invalid or contains non-numeric values
        """
        # Check for common format errors first
        if " and " in argument.lower() or " then " in argument.lower():
            raise ValueError(
                f"Invalid click format: '{argument}'. "
                f"Cannot combine multiple actions with 'and' or 'then'. "
                f"Each action must be separate in the action list."
            )

        parts = argument.split(",") if argument else []
        if len(parts) < 2:
            raise ValueError(
                f"Invalid click coordinate format: '{argument}'. Expected 'x, y' (comma-separated numeric values)"
            )
        try:
            x = float(parts[0].strip())
            y = float(parts[1].strip())
            return self._denormalize_coords(x, y)
        except (ValueError, IndexError) as e:
            raise ValueError(
                f"Failed to parse click coords '{argument}': {e}. "
                f"Coordinates must be comma-separated numeric values, e.g., 'click(500, 300)'"
            ) from e

    def _parse_drag_coords(self, argument: str) -> tuple[int, int, int, int]:
        """Parse drag coordinates from argument string.

        Args:
            argument: Coordinate string in format "x1, y1, x2, y2"

        Returns:
            Tuple of denormalized (x1, y1, x2, y2) coordinates

        Raises:
            ValueError: If coordinate format is invalid or contains non-numeric values
        """
        # Check for common format errors first
        if " and " in argument.lower() or " then " in argument.lower():
            raise ValueError(
                f"Invalid drag format: '{argument}'. "
                f"Cannot combine multiple actions with 'and' or 'then'. "
                f"Each action must be separate in the action list."
            )

        parts = argument.split(",") if argument else []
        if len(parts) != 4:
            raise ValueError(
                f"Invalid drag coordinate format: '{argument}'. "
                f"Expected 'x1, y1, x2, y2' (4 comma-separated numeric values)"
            )
        try:
            sx = float(parts[0].strip())
            sy = float(parts[1].strip())
            ex = float(parts[2].strip())
            ey = float(parts[3].strip())
            sx, sy = self._denormalize_coords(sx, sy)
            ex, ey = self._denormalize_coords(ex, ey)
            return sx, sy, ex, ey
        except (ValueError, IndexError) as e:
            raise ValueError(
                f"Failed to parse drag coords '{argument}': {e}. "
                f"Coordinates must be comma-separated numeric values, e.g., 'drag(100, 200, 300, 400)'"
            ) from e

    def _normalize_key(self, key: str) -> str:
        """Normalize key names for consistency.

        Maps common aliases to pyautogui-recognized key names.
        Handles underscore-separated key names (e.g., page_down -> pagedown).
        """
        key = key.strip().lower()

        # Normalize underscore-separated key names to pyautogui format
        # This handles common model outputs like page_down, print_screen, etc.
        # Synced from oagi.handler.utils.normalize_key
        hotkey_variations_mapping = {
            "pageup": ["page_up", "pageup", "pgup"],
            "pagedown": ["page_down", "pagedown", "pgdn"],
            "printscreen": ["print_screen", "printscreen", "prtsc", "prtscr"],
            "numlock": ["num_lock", "numlock"],
            "scrolllock": ["scroll_lock", "scrolllock"],
            "capslock": ["caps_lock", "caps", "capslock"],
        }
        for normalized, variations in hotkey_variations_mapping.items():
            if key in variations:
                return normalized

        # Windows-specific key mappings
        if key in ("windows", "super", "meta"):
            return "win"  # Windows key

        # macOS-specific key mappings
        if key == "cmd":
            return "command"

        # Control key alias (pyautogui uses 'ctrl', not 'control')
        if key == "control":
            return "ctrl"

        # Media key aliases
        if key == "mute":
            return "volumemute"
        if key == "play":
            return "playpause"

        return key

    def _validate_keys(self, keys: list[str]) -> None:
        """Validate that all keys are recognized by pyautogui.

        Args:
            keys: List of normalized key names

        Raises:
            ValueError: If any key is invalid, with helpful suggestions
        """
        invalid_keys = [k for k in keys if k and k not in PYAUTOGUI_VALID_KEYS]

        if invalid_keys:
            # Provide helpful suggestions for common mistakes
            suggestions = []
            for invalid_key in invalid_keys:
                if invalid_key in ("return", "ret"):
                    suggestions.append(f"'{invalid_key}' → use 'enter' or 'return'")
                elif invalid_key in ("delete", "del"):
                    suggestions.append(f"'{invalid_key}' → use 'delete' or 'del'")
                elif invalid_key in ("escape", "esc"):
                    suggestions.append(f"'{invalid_key}' → use 'escape' or 'esc'")
                elif invalid_key.startswith("num") and len(invalid_key) > 3:
                    suggestions.append(
                        f"'{invalid_key}' → numpad keys use format 'num0'-'num9'"
                    )
                else:
                    suggestions.append(f"'{invalid_key}' is not a valid key name")

            error_msg = "Invalid key name(s) in hotkey: " + ", ".join(suggestions)
            error_msg += f"\n\nValid keys include: {', '.join(sorted(list(PYAUTOGUI_VALID_KEYS)[:30]))}... (and more)"
            raise ValueError(error_msg)

    def _parse_hotkey(self, args_str: str) -> list[str]:
        """Parse hotkey string into list of keys.

        Args:
            args_str: Hotkey string (e.g., "ctrl+c", "alt+tab")

        Returns:
            List of normalized key names

        Raises:
            ValueError: If any key is invalid
        """
        # Remove parentheses if present
        args_str = args_str.strip("()")

        # Split by '+' or ',' to get individual keys
        # This handles both formats: "ctrl+c" and "alt, tab"
        if "+" in args_str:
            keys = [self._normalize_key(key) for key in args_str.split("+")]
        else:
            # Split by comma (handles "alt, tab" format from model output)
            keys = [self._normalize_key(key) for key in args_str.split(",")]

        # Validate all keys before returning
        self._validate_keys(keys)

        return keys

    def _convert_single_action(self, action: Any) -> list[str]:
        action_type = action.type.value
        # Strip outer parentheses from argument, similar to official handler
        argument = (action.argument or "").strip("()")

        drag_duration = self.pyautogui_config.drag_duration
        scroll_default = self.pyautogui_config.scroll_amount
        wait_default = self.pyautogui_config.wait_duration

        if action_type == ActionType.CLICK.value:
            x, y = self._parse_click_coords(argument)
            return [f"pyautogui.click(x={x}, y={y})"]

        if action_type == ActionType.LEFT_DOUBLE.value:
            x, y = self._parse_click_coords(argument)
            return [f"pyautogui.doubleClick(x={x}, y={y})"]

        if action_type == ActionType.LEFT_TRIPLE.value:
            x, y = self._parse_click_coords(argument)
            return [f"pyautogui.tripleClick(x={x}, y={y})"]

        if action_type == ActionType.RIGHT_SINGLE.value:
            x, y = self._parse_click_coords(argument)
            return [f"pyautogui.rightClick(x={x}, y={y})"]

        if action_type == ActionType.DRAG.value:
            sx, sy, ex, ey = self._parse_drag_coords(argument)
            return [
                f"pyautogui.moveTo({sx}, {sy})",
                f"pyautogui.dragTo({ex}, {ey}, duration={drag_duration})",
            ]

        if action_type == ActionType.HOTKEY.value:
            keys = self._parse_hotkey(argument)
            # Validate keys are not empty (already validated in _parse_hotkey)
            valid_keys = [k for k in keys if k]
            if not valid_keys:
                raise ValueError(
                    f"Invalid hotkey format: '{argument}'. "
                    f"Expected key names like 'ctrl+c', 'alt+tab', got empty or invalid keys"
                )
            # Check if this is a caps lock key press
            if len(valid_keys) == 1 and valid_keys[0] == "capslock":
                if self.caps_manager.should_use_system_capslock():
                    # System mode: use OS-level caps lock
                    hotkey_interval = self.pyautogui_config.hotkey_interval
                    return [f"pyautogui.hotkey('capslock', interval={hotkey_interval})"]
                else:
                    # Session mode: toggle internal state (no actual key press needed in conversion)
                    self.caps_manager.toggle()
                    return []  # No pyautogui command needed for session mode
            else:
                # Regular hotkey combination
                keys_str = ", ".join(repr(k) for k in valid_keys)
                hotkey_interval = self.pyautogui_config.hotkey_interval
                return [f"pyautogui.hotkey({keys_str}, interval={hotkey_interval})"]

        if action_type == ActionType.TYPE.value:
            # Remove quotes if present
            text = argument.strip("\"'")

            # Apply caps lock transformation if needed
            text = self.caps_manager.transform_text(text)
            return [make_type_command(text)]

        if action_type == ActionType.SCROLL.value:
            parts = [p.strip() for p in argument.split(",")]
            if len(parts) != 3:
                raise ValueError(
                    f"Invalid scroll format: '{argument}'. "
                    f"Expected 'x, y, direction' (3 comma-separated values), got {len(parts)} parts"
                )
            try:
                x = float(parts[0])
                y = float(parts[1])
            except (ValueError, IndexError) as e:
                raise ValueError(
                    f"Invalid scroll coordinates: '{argument}'. "
                    f"x and y must be numeric values, e.g., 'scroll(500, 300, up)'"
                ) from e

            x, y = self._denormalize_coords(x, y)
            direction = parts[2].lower().strip()

            if direction == "up":
                amount = scroll_default
            elif direction == "down":
                amount = -scroll_default
            else:
                raise ValueError(
                    f"Invalid scroll direction: '{direction}' in '{argument}'. Expected 'up' or 'down'"
                )

            return [f"pyautogui.moveTo({x}, {y})", f"pyautogui.scroll({amount})"]

        if action_type == ActionType.WAIT.value:
            try:
                seconds = float(argument) if argument else float(wait_default)
            except ValueError:
                raise ValueError(
                    f"Invalid wait duration: '{argument}'. Expected numeric value in seconds, e.g., 'wait(2.0)'"
                ) from None
            return [f"WAIT({seconds})"]

        if action_type == ActionType.FINISH.value:
            # Task completion action
            self.logger.info("Task completion action -> DONE")
            return ["DONE"]

        if action_type == ActionType.FAIL.value:
            # Task infeasible action
            self.logger.info("Task infeasible action -> FAIL")
            return ["FAIL"]

        if action_type == ActionType.CALL_USER.value:
            # User intervention requested - not an error, just no-op
            self.logger.info("User intervention requested")
            return []

        # Unknown action type - raise error to guide model
        raise ValueError(
            f"Unknown action type: '{action_type}'. "
            f"Supported types: click, left_double, left_triple, right_single, drag, "
            f"hotkey, type, scroll, wait, finish, fail"
        )

    # ------------------------------------------------------------------
    # Public: convert an action string into a runtime step dict
    # ------------------------------------------------------------------
    def action_string_to_step(self, action: str) -> dict[str, Any]:
        """Convert a single action string into a step for runtime/do API.

        Mirrors previous TaskExecutor._convert_action_to_step behavior.
        """
        action_str = str(action).strip()

        if not action_str:
            raise ValueError("Empty action string — invalid model output format")

        # Special markers
        upper = action_str.upper()
        if upper in ["DONE", "FAIL"]:
            return {"type": "sleep", "parameters": {"seconds": 0}}

        # WAIT(seconds)
        wait_match = re.match(
            r"^WAIT\((?P<sec>[0-9]*\.?[0-9]+)\)$", action_str, re.IGNORECASE
        )
        if wait_match:
            seconds = float(wait_match.group("sec"))
            return {"type": "sleep", "parameters": {"seconds": seconds}}

        # pyautogui code path - use direct execution for better performance
        # This avoids spawning a new Python process for each action
        # PynputController and _smart_paste must also use this path to preserve X11 context
        action_lower = action_str.lower()
        if (
            "pyautogui" in action_lower
            or "pynputcontroller" in action_lower
            or "_smart_paste" in action_lower
        ):
            return {
                "type": "pyautogui",
                "parameters": {
                    "code": action_str,
                },
            }

        # Default: shell command
        return {
            "type": "execute",
            "parameters": {"command": action_str, "shell": True},
        }


# Backward compatibility alias
OagiActionConverter = PyautoguiActionConvertor
