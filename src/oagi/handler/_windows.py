# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

"""Windows-specific keyboard input handling.

This module provides typewrite_exact() which types text exactly as specified,
ignoring the system's capslock state by using SendInput with KEYEVENTF_UNICODE.
"""

import ctypes
import time
from ctypes import wintypes

INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [
            ("ki", KEYBDINPUT),
            ("mi", MOUSEINPUT),
            ("hi", HARDWAREINPUT),
        ]

    _anonymous_ = ("i",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("i", _I),
    ]


# Configure SendInput with proper argtypes for 64-bit compatibility
SendInput = ctypes.windll.user32.SendInput
SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
SendInput.restype = wintypes.UINT


def typewrite_exact(text: str, interval: float = 0.01) -> None:
    """Type text exactly using Unicode input - ignores capslock, keyboard layout, etc.

    This function uses SendInput with KEYEVENTF_UNICODE to send characters
    directly by their Unicode codepoint, completely bypassing keyboard state
    (capslock, layout, etc.).

    Args:
        text: The text to type exactly as specified
        interval: Time in seconds between each character (default: 0.01)
    """
    for char in text:
        inputs = (INPUT * 2)()

        # Key down
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].ki.wScan = ord(char)
        inputs[0].ki.dwFlags = KEYEVENTF_UNICODE

        # Key up
        inputs[1].type = INPUT_KEYBOARD
        inputs[1].ki.wScan = ord(char)
        inputs[1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP

        SendInput(2, inputs, ctypes.sizeof(INPUT))

        if interval > 0:
            time.sleep(interval)
