# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Shared utilities for action handling and conversion.

This module provides common functionality used by both PyautoguiActionHandler
(for local execution) and action converters (for remote execution).
"""

import sys

# =============================================================================
# Key Normalization Mapping
# =============================================================================

# Unified key mapping - normalizes various key name formats to pyautogui names
KEY_MAP: dict[str, str] = {
    # Modifier keys
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "shift": "shift",
    "cmd": "command",
    "command": "command",
    "meta": "win",
    "super": "win",
    "windows": "win",
    "win": "win",
    # Enter/Return
    "return": "enter",
    "enter": "enter",
    # Escape
    "escape": "escape",
    "esc": "escape",
    # Page navigation
    "pageup": "pageup",
    "page_up": "pageup",
    "pgup": "pageup",
    "pagedown": "pagedown",
    "page_down": "pagedown",
    "pgdn": "pagedown",
    # Lock keys
    "capslock": "capslock",
    "caps_lock": "capslock",
    "caps": "capslock",
    "numlock": "numlock",
    "num_lock": "numlock",
    "scrolllock": "scrolllock",
    "scroll_lock": "scrolllock",
    # Print screen
    "printscreen": "printscreen",
    "print_screen": "printscreen",
    "prtsc": "printscreen",
    "prtscr": "printscreen",
    # Media keys
    "mute": "volumemute",
    "play": "playpause",
}

# Valid pyautogui key names
PYAUTOGUI_VALID_KEYS: frozenset[str] = frozenset(
    {
        # Alphabet keys
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "h",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",
        "o",
        "p",
        "q",
        "r",
        "s",
        "t",
        "u",
        "v",
        "w",
        "x",
        "y",
        "z",
        # Number keys
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        # Function keys
        "f1",
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f7",
        "f8",
        "f9",
        "f10",
        "f11",
        "f12",
        "f13",
        "f14",
        "f15",
        "f16",
        "f17",
        "f18",
        "f19",
        "f20",
        "f21",
        "f22",
        "f23",
        "f24",
        # Navigation keys
        "up",
        "down",
        "left",
        "right",
        "home",
        "end",
        "pageup",
        "pagedown",
        "pgup",
        "pgdn",
        # Editing keys
        "backspace",
        "delete",
        "del",
        "insert",
        "enter",
        "return",
        "tab",
        "space",
        # Modifier keys (with left/right variants)
        "shift",
        "shiftleft",
        "shiftright",
        "ctrl",
        "ctrlleft",
        "ctrlright",
        "alt",
        "altleft",
        "altright",
        "option",
        "optionleft",
        "optionright",
        "command",
        "win",
        "winleft",
        "winright",
        "fn",
        # Lock keys
        "capslock",
        "numlock",
        "scrolllock",
        # Special keys
        "esc",
        "escape",
        "pause",
        "printscreen",
        "prtsc",
        "prtscr",
        "prntscrn",
        "print",
        "apps",
        "clear",
        "sleep",
        # Symbols
        "!",
        "@",
        "#",
        "$",
        "%",
        "^",
        "&",
        "*",
        "(",
        ")",
        "-",
        "_",
        "=",
        "+",
        "[",
        "]",
        "{",
        "}",
        "\\",
        "|",
        ";",
        ":",
        "'",
        '"',
        ",",
        ".",
        "<",
        ">",
        "/",
        "?",
        "`",
        "~",
        # Numpad keys
        "num0",
        "num1",
        "num2",
        "num3",
        "num4",
        "num5",
        "num6",
        "num7",
        "num8",
        "num9",
        "divide",
        "multiply",
        "subtract",
        "add",
        "decimal",
        # Media keys
        "volumeup",
        "volumedown",
        "volumemute",
        "playpause",
        "stop",
        "nexttrack",
        "prevtrack",
        # Browser keys
        "browserback",
        "browserforward",
        "browserrefresh",
        "browserstop",
        "browsersearch",
        "browserfavorites",
        "browserhome",
        # Application launch keys
        "launchapp1",
        "launchapp2",
        "launchmail",
        "launchmediaselect",
    }
)


# =============================================================================
# Coordinate Scaling
# =============================================================================


class CoordinateScaler:
    """Handles coordinate scaling between different coordinate systems.

    This class provides reusable coordinate transformation logic used by both
    PyautoguiActionHandler (local execution) and action converters (remote execution).

    Args:
        source_width: Width of the source coordinate space (e.g., 1000 for OAGI)
        source_height: Height of the source coordinate space
        target_width: Width of the target coordinate space (e.g., screen width)
        target_height: Height of the target coordinate space
        origin_x: X offset of the target coordinate origin (for multi-monitor)
        origin_y: Y offset of the target coordinate origin (for multi-monitor)
    """

    def __init__(
        self,
        source_width: int,
        source_height: int,
        target_width: int,
        target_height: int,
        origin_x: int = 0,
        origin_y: int = 0,
    ):
        self.source_width = source_width
        self.source_height = source_height
        self.target_width = target_width
        self.target_height = target_height
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.scale_x = target_width / source_width
        self.scale_y = target_height / source_height

    def scale(
        self,
        x: int | float,
        y: int | float,
        *,
        clamp: bool = True,
        prevent_failsafe: bool = False,
    ) -> tuple[int, int]:
        """Scale coordinates from source to target space.

        Args:
            x: X coordinate in source space
            y: Y coordinate in source space
            clamp: If True, clamp to valid target range
            prevent_failsafe: If True, offset corner coordinates by 1 pixel
                             (prevents PyAutoGUI fail-safe trigger)

        Returns:
            Tuple of (target_x, target_y) in target coordinate space
        """
        scaled_x = round(x * self.scale_x)
        scaled_y = round(y * self.scale_y)

        if clamp:
            # Clamp to valid range
            scaled_x = max(0, min(scaled_x, self.target_width - 1))
            scaled_y = max(0, min(scaled_y, self.target_height - 1))

        if prevent_failsafe:
            # Prevent PyAutoGUI fail-safe by adjusting corner coordinates
            if scaled_x < 1:
                scaled_x = 1
            elif scaled_x > self.target_width - 2:
                scaled_x = self.target_width - 2
            if scaled_y < 1:
                scaled_y = 1
            elif scaled_y > self.target_height - 2:
                scaled_y = self.target_height - 2

        # Add origin offset (for multi-monitor support)
        return scaled_x + self.origin_x, scaled_y + self.origin_y

    def set_origin(self, origin_x: int, origin_y: int) -> None:
        """Update the origin offset."""
        self.origin_x = origin_x
        self.origin_y = origin_y

    def set_target_size(self, width: int, height: int) -> None:
        """Update the target size and recalculate scale factors."""
        self.target_width = width
        self.target_height = height
        self.scale_x = width / self.source_width
        self.scale_y = height / self.source_height


# =============================================================================
# Key Normalization Functions
# =============================================================================


def normalize_key(key: str, *, macos_ctrl_to_cmd: bool = False) -> str:
    """Normalize a key name to pyautogui format.

    Args:
        key: Key name to normalize (e.g., "ctrl", "Control", "page_down")
        macos_ctrl_to_cmd: If True and on macOS, remap 'ctrl' to 'command'

    Returns:
        Normalized key name (e.g., "ctrl", "pagedown")
    """
    key = key.strip().lower()
    normalized = KEY_MAP.get(key, key)

    # Remap ctrl to command on macOS if enabled
    if macos_ctrl_to_cmd and sys.platform == "darwin" and normalized == "ctrl":
        return "command"

    return normalized


def parse_hotkey(
    hotkey_str: str,
    *,
    macos_ctrl_to_cmd: bool = False,
    validate: bool = True,
) -> list[str]:
    """Parse a hotkey string into a list of normalized key names.

    Args:
        hotkey_str: Hotkey string (e.g., "ctrl+c", "alt, tab", "Shift+Enter")
        macos_ctrl_to_cmd: If True and on macOS, remap 'ctrl' to 'command'
        validate: If True, validate keys against PYAUTOGUI_VALID_KEYS

    Returns:
        List of normalized key names (e.g., ["ctrl", "c"])

    Raises:
        ValueError: If validate=True and any key is invalid
    """
    # Remove parentheses if present
    hotkey_str = hotkey_str.strip("()")

    # Split by '+' or ',' to get individual keys
    if "+" in hotkey_str:
        keys = [
            normalize_key(k, macos_ctrl_to_cmd=macos_ctrl_to_cmd)
            for k in hotkey_str.split("+")
        ]
    else:
        keys = [
            normalize_key(k, macos_ctrl_to_cmd=macos_ctrl_to_cmd)
            for k in hotkey_str.split(",")
        ]

    # Filter empty strings
    keys = [k for k in keys if k]

    if validate:
        validate_keys(keys)

    return keys


def validate_keys(keys: list[str]) -> None:
    """Validate that all keys are recognized by pyautogui.

    Args:
        keys: List of normalized key names

    Raises:
        ValueError: If any key is invalid, with helpful suggestions
    """
    invalid_keys = [k for k in keys if k and k not in PYAUTOGUI_VALID_KEYS]

    if invalid_keys:
        suggestions = []
        for invalid_key in invalid_keys:
            if invalid_key in ("ret",):
                suggestions.append(f"'{invalid_key}' -> use 'enter' or 'return'")
            elif invalid_key.startswith("num") and len(invalid_key) > 3:
                suggestions.append(
                    f"'{invalid_key}' -> numpad keys use format 'num0'-'num9'"
                )
            else:
                suggestions.append(f"'{invalid_key}' is not a valid key name")

        error_msg = "Invalid key name(s) in hotkey: " + ", ".join(suggestions)
        valid_sample = ", ".join(sorted(list(PYAUTOGUI_VALID_KEYS)[:30]))
        error_msg += f"\n\nValid keys include: {valid_sample}... (and more)"
        raise ValueError(error_msg)


# =============================================================================
# Coordinate Parsing Functions
# =============================================================================


def parse_click_coords(
    argument: str,
    scaler: CoordinateScaler,
    *,
    prevent_failsafe: bool = False,
) -> tuple[int, int]:
    """Parse click coordinates from argument string.

    Args:
        argument: Coordinate string in format "x, y"
        scaler: CoordinateScaler instance for coordinate transformation
        prevent_failsafe: If True, offset corner coordinates

    Returns:
        Tuple of (x, y) in target coordinate space

    Raises:
        ValueError: If coordinate format is invalid
    """
    # Check for common format errors
    if " and " in argument.lower() or " then " in argument.lower():
        raise ValueError(
            f"Invalid click format: '{argument}'. "
            "Cannot combine multiple actions with 'and' or 'then'."
        )

    parts = argument.split(",") if argument else []
    if len(parts) < 2:
        raise ValueError(
            f"Invalid click coordinate format: '{argument}'. "
            "Expected 'x, y' (comma-separated numeric values)"
        )

    try:
        x = float(parts[0].strip())
        y = float(parts[1].strip())
        return scaler.scale(x, y, prevent_failsafe=prevent_failsafe)
    except (ValueError, IndexError) as e:
        raise ValueError(
            f"Failed to parse click coords '{argument}': {e}. "
            "Coordinates must be comma-separated numeric values."
        ) from e


def parse_drag_coords(
    argument: str,
    scaler: CoordinateScaler,
    *,
    prevent_failsafe: bool = False,
) -> tuple[int, int, int, int]:
    """Parse drag coordinates from argument string.

    Args:
        argument: Coordinate string in format "x1, y1, x2, y2"
        scaler: CoordinateScaler instance for coordinate transformation
        prevent_failsafe: If True, offset corner coordinates

    Returns:
        Tuple of (x1, y1, x2, y2) in target coordinate space

    Raises:
        ValueError: If coordinate format is invalid
    """
    # Check for common format errors
    if " and " in argument.lower() or " then " in argument.lower():
        raise ValueError(
            f"Invalid drag format: '{argument}'. "
            "Cannot combine multiple actions with 'and' or 'then'."
        )

    parts = argument.split(",") if argument else []
    if len(parts) != 4:
        raise ValueError(
            f"Invalid drag coordinate format: '{argument}'. "
            "Expected 'x1, y1, x2, y2' (4 comma-separated numeric values)"
        )

    try:
        sx = float(parts[0].strip())
        sy = float(parts[1].strip())
        ex = float(parts[2].strip())
        ey = float(parts[3].strip())
        x1, y1 = scaler.scale(sx, sy, prevent_failsafe=prevent_failsafe)
        x2, y2 = scaler.scale(ex, ey, prevent_failsafe=prevent_failsafe)
        return x1, y1, x2, y2
    except (ValueError, IndexError) as e:
        raise ValueError(
            f"Failed to parse drag coords '{argument}': {e}. "
            "Coordinates must be comma-separated numeric values."
        ) from e


def parse_scroll_coords(
    argument: str,
    scaler: CoordinateScaler,
    *,
    prevent_failsafe: bool = False,
) -> tuple[int, int, str]:
    """Parse scroll coordinates and direction from argument string.

    Args:
        argument: Scroll string in format "x, y, direction"
        scaler: CoordinateScaler instance for coordinate transformation
        prevent_failsafe: If True, offset corner coordinates

    Returns:
        Tuple of (x, y, direction) where direction is 'up' or 'down'

    Raises:
        ValueError: If format is invalid
    """
    parts = [p.strip() for p in argument.split(",")]
    if len(parts) != 3:
        raise ValueError(
            f"Invalid scroll format: '{argument}'. "
            "Expected 'x, y, direction' (e.g., '500, 300, up')"
        )

    try:
        x = float(parts[0])
        y = float(parts[1])
        direction = parts[2].lower()

        if direction not in ("up", "down"):
            raise ValueError(
                f"Invalid scroll direction: '{direction}'. Use 'up' or 'down'."
            )

        scaled_x, scaled_y = scaler.scale(x, y, prevent_failsafe=prevent_failsafe)
        return scaled_x, scaled_y, direction
    except (ValueError, IndexError) as e:
        if "scroll direction" in str(e):
            raise
        raise ValueError(
            f"Failed to parse scroll coords '{argument}': {e}. "
            "Format: 'x, y, direction'"
        ) from e


# =============================================================================
# Handler Utility Functions
# =============================================================================


def reset_handler(handler) -> None:
    """Reset handler state if supported.

    Uses duck-typing to check if the handler has a reset() method.
    This allows handlers to reset their internal state (e.g., capslock state)
    at the start of a new automation task.

    Args:
        handler: The action handler to reset
    """
    if hasattr(handler, "reset"):
        handler.reset()


def configure_handler_delay(handler, step_delay: float) -> None:
    """Configure handler's post_batch_delay from agent's step_delay.

    Uses duck-typing to check if the handler has a config with post_batch_delay.
    This allows agents to control the delay after action execution.

    Args:
        handler: The action handler to configure
        step_delay: The delay in seconds to set
    """
    if hasattr(handler, "config") and hasattr(handler.config, "post_batch_delay"):
        handler.config.post_batch_delay = step_delay
