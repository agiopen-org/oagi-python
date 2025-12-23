# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
import importlib
from typing import TYPE_CHECKING

from .utils import reset_handler

# Lazy imports for pyautogui-dependent modules to avoid import errors on headless systems
_LAZY_IMPORTS: dict[str, str] = {
    "AsyncPyautoguiActionHandler": "oagi.handler.async_pyautogui_action_handler",
    "AsyncScreenshotMaker": "oagi.handler.async_screenshot_maker",
    "PILImage": "oagi.handler.pil_image",
    "PyautoguiActionHandler": "oagi.handler.pyautogui_action_handler",
    "PyautoguiConfig": "oagi.handler.pyautogui_action_handler",
    "ScreenshotMaker": "oagi.handler.screenshot_maker",
    "AsyncYdotoolActionHandler": "oagi.handler.async_ydotool_action_handler",
    "YdotoolActionHandler": "oagi.handler.ydotool_action_handler",
    "YdotoolConfig": "oagi.handler.ydotool_action_handler",
}

if TYPE_CHECKING:
    from oagi.handler.async_pyautogui_action_handler import AsyncPyautoguiActionHandler
    from oagi.handler.async_screenshot_maker import AsyncScreenshotMaker
    from oagi.handler.async_ydotool_action_handler import AsyncYdotoolActionHandler
    from oagi.handler.pil_image import PILImage
    from oagi.handler.pyautogui_action_handler import (
        PyautoguiActionHandler,
        PyautoguiConfig,
    )
    from oagi.handler.screenshot_maker import ScreenshotMaker
    from oagi.handler.ydotool_action_handler import YdotoolActionHandler, YdotoolConfig


def __getattr__(name: str):
    """Lazy import for pyautogui-dependent modules."""
    if name in _LAZY_IMPORTS:
        module = importlib.import_module(_LAZY_IMPORTS[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Return all public names including lazy imports."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "PILImage",
    "PyautoguiActionHandler",
    "PyautoguiConfig",
    "AsyncPyautoguiActionHandler",
    "ScreenshotMaker",
    "AsyncScreenshotMaker",
    "reset_handler",
    "YdotoolConfig",
    "YdotoolActionHandler",
    "AsyncYdotoolActionHandler",
]
