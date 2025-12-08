# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import re
from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CLICK = "click"
    LEFT_DOUBLE = "left_double"
    LEFT_TRIPLE = "left_triple"
    RIGHT_SINGLE = "right_single"
    DRAG = "drag"
    HOTKEY = "hotkey"
    TYPE = "type"
    SCROLL = "scroll"
    FINISH = "finish"
    WAIT = "wait"
    CALL_USER = "call_user"


class Action(BaseModel):
    type: ActionType = Field(..., description="Type of action to perform")
    argument: str = Field(..., description="Action argument in the specified format")
    count: int | None = Field(
        default=1, ge=1, description="Number of times to repeat the action"
    )


def parse_coords(args_str: str) -> tuple[int, int] | None:
    """Extract x, y coordinates from argument string.

    Args:
        args_str: Argument string in format "x, y" (normalized 0-1000 range)

    Returns:
        Tuple of (x, y) coordinates, or None if parsing fails
    """
    match = re.match(r"(\d+),\s*(\d+)", args_str)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def parse_drag_coords(args_str: str) -> tuple[int, int, int, int] | None:
    """Extract x1, y1, x2, y2 coordinates from drag argument string.

    Args:
        args_str: Argument string in format "x1, y1, x2, y2" (normalized 0-1000 range)

    Returns:
        Tuple of (x1, y1, x2, y2) coordinates, or None if parsing fails
    """
    match = re.match(r"(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", args_str)
    if not match:
        return None
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        int(match.group(4)),
    )


def parse_scroll(args_str: str) -> tuple[int, int, str] | None:
    """Extract x, y, direction from scroll argument string.

    Args:
        args_str: Argument string in format "x, y, direction" (normalized 0-1000 range)

    Returns:
        Tuple of (x, y, direction) where direction is "up" or "down", or None if parsing fails
    """
    match = re.match(r"(\d+),\s*(\d+),\s*(\w+)", args_str)
    if not match:
        return None
    direction = match.group(3).lower()
    if direction not in ("up", "down"):
        return None
    return int(match.group(1)), int(match.group(2)), direction
