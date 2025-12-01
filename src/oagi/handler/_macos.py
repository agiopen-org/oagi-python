# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

"""macOS-specific keyboard and mouse input handling.

This module provides:
- macos_click(): Fix for PyAutoGUI multi-click bug on macOS
- typewrite_exact(): Type text exactly, ignoring system capslock state
"""

import time

import pyautogui

from ..exceptions import check_optional_dependency

check_optional_dependency("Quartz", "macOS multiple clicks", "desktop")
import Quartz  # noqa: E402

# macOS virtual key codes for typeable characters
KEYCODE_MAP = {
    "a": 0x00,
    "b": 0x0B,
    "c": 0x08,
    "d": 0x02,
    "e": 0x0E,
    "f": 0x03,
    "g": 0x05,
    "h": 0x04,
    "i": 0x22,
    "j": 0x26,
    "k": 0x28,
    "l": 0x25,
    "m": 0x2E,
    "n": 0x2D,
    "o": 0x1F,
    "p": 0x23,
    "q": 0x0C,
    "r": 0x0F,
    "s": 0x01,
    "t": 0x11,
    "u": 0x20,
    "v": 0x09,
    "w": 0x0D,
    "x": 0x07,
    "y": 0x10,
    "z": 0x06,
    "1": 0x12,
    "2": 0x13,
    "3": 0x14,
    "4": 0x15,
    "5": 0x17,
    "6": 0x16,
    "7": 0x1A,
    "8": 0x1C,
    "9": 0x19,
    "0": 0x1D,
    " ": 0x31,  # space
    "-": 0x1B,
    "=": 0x18,
    "[": 0x21,
    "]": 0x1E,
    "\\": 0x2A,
    ";": 0x29,
    "'": 0x27,
    "`": 0x32,
    ",": 0x2B,
    ".": 0x2F,
    "/": 0x2C,
    "\t": 0x30,  # tab
    "\n": 0x24,  # return
}

# Characters that require shift key (on US keyboard layout)
SHIFT_CHARS = set('~!@#$%^&*()_+{}|:"<>?ABCDEFGHIJKLMNOPQRSTUVWXYZ')

# Mapping of shifted characters to their base key
SHIFT_KEY_MAP = {
    "~": "`",
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    "{": "[",
    "}": "]",
    "|": "\\",
    ":": ";",
    '"': "'",
    "<": ",",
    ">": ".",
    "?": "/",
}


def typewrite_exact(text: str, interval: float = 0.01) -> None:
    """Type text exactly as specified, ignoring system capslock state.

    This function uses Quartz CGEventCreateKeyboardEvent with explicit
    flag control via CGEventSetFlags() to type each character with the
    correct case, regardless of the system's capslock state.

    Args:
        text: The text to type exactly as specified
        interval: Time in seconds between each character (default: 0.01)
    """
    for char in text:
        # Determine if this character needs shift
        needs_shift = char in SHIFT_CHARS

        # Get the base key (for shifted chars, look up the unshifted version)
        if char.isupper():
            base_char = char.lower()
        elif char in SHIFT_KEY_MAP:
            base_char = SHIFT_KEY_MAP[char]
        else:
            base_char = char

        # Get keycode for the base character
        keycode = KEYCODE_MAP.get(base_char)
        if keycode is None:
            # Character not in our keycode map, skip it
            continue

        # Set flags: shift if needed, otherwise clear all flags
        flags = Quartz.kCGEventFlagMaskShift if needs_shift else 0

        # Key down
        event_down = Quartz.CGEventCreateKeyboardEvent(None, keycode, True)
        Quartz.CGEventSetFlags(event_down, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)

        # Key up
        event_up = Quartz.CGEventCreateKeyboardEvent(None, keycode, False)
        Quartz.CGEventSetFlags(event_up, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)

        if interval > 0:
            time.sleep(interval)


def macos_click(x: int, y: int, clicks: int = 1) -> None:
    """
    Execute a mouse click sequence on macOS with correct click state.

    This avoids the PyAutoGUI bug where multi-clicks are sent as separate
    single clicks (clickState=1), which macOS interprets as distinct events
    rather than double/triple clicks.

    Check https://github.com/asweigart/pyautogui/issues/672

    Args:
        x: X coordinate
        y: Y coordinate
        clicks: Number of clicks (1=single, 2=double, 3=triple)
    """
    # Move to position first using pyautogui to ensure consistency
    pyautogui.moveTo(x, y)

    point = Quartz.CGPoint(x=x, y=y)

    # Create and post events for each click in the sequence
    for i in range(1, clicks + 1):
        # Create Down/Up events
        mouse_down = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventLeftMouseDown, point, Quartz.kCGMouseButtonLeft
        )
        mouse_up = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventLeftMouseUp, point, Quartz.kCGMouseButtonLeft
        )

        # Set the click state (1 for first click, 2 for second, etc.)
        Quartz.CGEventSetIntegerValueField(
            mouse_down, Quartz.kCGMouseEventClickState, i
        )
        Quartz.CGEventSetIntegerValueField(mouse_up, Quartz.kCGMouseEventClickState, i)

        # Post events
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, mouse_down)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, mouse_up)
