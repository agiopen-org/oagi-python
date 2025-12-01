# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
from oagi.handler.async_pyautogui_action_handler import AsyncPyautoguiActionHandler
from oagi.handler.async_screenshot_maker import AsyncScreenshotMaker
from oagi.handler.pil_image import PILImage
from oagi.handler.pyautogui_action_handler import (
    PyautoguiActionHandler,
    PyautoguiConfig,
)
from oagi.handler.screenshot_maker import ScreenshotMaker


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


__all__ = [
    "PILImage",
    "PyautoguiActionHandler",
    "PyautoguiConfig",
    "AsyncPyautoguiActionHandler",
    "ScreenshotMaker",
    "AsyncScreenshotMaker",
    "reset_handler",
]
