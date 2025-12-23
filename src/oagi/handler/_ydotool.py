# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""
Taken from /usr/include/linux/input-event-codes.h

The keys supported in this mapping are the same as the keys supported in pyautogui.
"""

KEYCODE_MAP = {
    # Letters
    "a": 30,
    "s": 31,
    "d": 32,
    "f": 33,
    "h": 35,
    "g": 34,
    "z": 44,
    "x": 45,
    "c": 46,
    "v": 47,
    "b": 48,
    "q": 16,
    "w": 17,
    "e": 18,
    "r": 19,
    "y": 21,
    "t": 20,
    "o": 24,
    "u": 22,
    "i": 23,
    "p": 25,
    "l": 38,
    "j": 36,
    "k": 37,
    "n": 49,
    "m": 50,
    # Numbers and shifted symbols
    "1": 2,
    "!": 2,
    "2": 3,
    "@": 3,
    "3": 4,
    "#": 4,
    "4": 5,
    "$": 5,
    "5": 6,
    "%": 6,
    "6": 7,
    "^": 7,
    "7": 8,
    "&": 8,
    "8": 9,
    "*": 9,
    "9": 10,
    "(": 10,
    "0": 11,
    ")": 11,
    # Punctuation and symbols
    "-": 12,
    "_": 12,  # KEY_MINUS
    "=": 13,
    "+": 13,  # KEY_EQUAL
    "[": 26,
    "{": 26,  # KEY_LEFTBRACE
    "]": 27,
    "}": 27,  # KEY_RIGHTBRACE
    ";": 39,
    ":": 39,  # KEY_SEMICOLON
    "'": 40,
    '"': 40,  # KEY_APOSTROPHE
    "`": 41,
    "~": 41,  # KEY_GRAVE
    "\\": 43,
    "|": 43,  # KEY_BACKSLASH
    ",": 51,
    "<": 51,  # KEY_COMMA
    ".": 52,
    ">": 52,  # KEY_DOT
    "/": 53,
    "?": 53,  # KEY_SLASH
    # Whitespace
    " ": 57,
    "space": 57,
    "\t": 15,
    "tab": 15,
    # Enter / Backspace / Esc
    "\r": 28,
    "\n": 28,
    "enter": 28,
    "return": 28,
    "backspace": 14,
    "\b": 14,
    "esc": 1,
    "escape": 1,
    # Modifiers
    "shift": 42,
    "shiftleft": 42,
    "shiftright": 54,
    "capslock": 58,
    "ctrl": 29,
    "ctrlleft": 29,
    "ctrlright": 97,
    "alt": 56,
    "altleft": 56,
    "option": 56,
    "optionleft": 56,
    "optionright": 100,
    "command": 125,  # map to KEY_LEFTMETA
    "fn": 464,  # KEY_FN (0x1d0)
    # Function keys
    "f1": 59,
    "f2": 60,
    "f3": 61,
    "f4": 62,
    "f5": 63,
    "f6": 64,
    "f7": 65,
    "f8": 66,
    "f9": 67,
    "f10": 68,
    "f11": 87,
    "f12": 88,
    "f13": 183,
    "f14": 184,
    "f15": 185,
    "f16": 186,
    "f17": 187,
    "f18": 188,
    "f19": 189,
    "f20": 190,
    # Navigation
    "home": 102,
    "end": 107,
    "pageup": 104,
    "pgup": 104,
    "pagedown": 109,
    "pgdn": 109,
    "left": 105,
    "right": 106,
    "up": 103,
    "down": 108,
    "del": 111,
    "delete": 111,
    # Media
    "volumeup": 115,
    "volumedown": 114,
    "volumemute": 113,
    # Locale-specific keys
    "yen": 124,  # KEY_YEN
    "eisu": 85,  # mapped to KEY_ZENKAKUHANKAKU (common JIS toggle)
    "kana": 90,  # KEY_KATAKANA
    "help": 138,  # KEY_HELP
}
