# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import pyautogui

from ..exceptions import check_optional_dependency

check_optional_dependency("Quartz", "macOS multiple clicks", "desktop")
import Quartz  # noqa: E402


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
