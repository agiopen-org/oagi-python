# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
import importlib
import importlib.metadata
from typing import TYPE_CHECKING

__version__ = importlib.metadata.version("oagi-core")

from oagi.actor import Actor, AsyncActor, AsyncShortTask, AsyncTask, ShortTask, Task
from oagi.client import AsyncClient, SyncClient
from oagi.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    NotFoundError,
    OAGIError,
    RateLimitError,
    RequestTimeoutError,
    ServerError,
    ValidationError,
    check_optional_dependency,
)
from oagi.types import ImageConfig
from oagi.types.models import (
    ErrorDetail,
    ErrorResponse,
    GenerateResponse,
    UploadFileResponse,
)

# Lazy imports for optional dependency modules
# Format: name -> (module_path, package_to_check, extra_name)
# package_to_check is None if no optional dependency is required
_LAZY_IMPORTS_DATA: dict[str, tuple[str, str | None, str | None]] = {
    # Action converters (no optional dependencies)
    "PyautoguiActionConvertor": (
        "oagi.converters.pyautogui_action_converter",
        None,
        None,
    ),
    "BaseActionConverter": ("oagi.converters.base", None, None),
    # Desktop handlers (require pyautogui/PIL)
    "AsyncPyautoguiActionHandler": (
        "oagi.handler.async_pyautogui_action_handler",
        "pyautogui",
        "desktop",
    ),
    "AsyncScreenshotMaker": ("oagi.handler.async_screenshot_maker", "PIL", "desktop"),
    "PILImage": ("oagi.handler.pil_image", "PIL", "desktop"),
    "PyautoguiActionHandler": (
        "oagi.handler.pyautogui_action_handler",
        "pyautogui",
        "desktop",
    ),
    "PyautoguiConfig": ("oagi.handler.utils", None, None),
    "ScreenshotMaker": ("oagi.handler.screenshot_maker", "PIL", "desktop"),
    # Agent modules (lazy to avoid circular imports)
    "AsyncDefaultAgent": ("oagi.agent.default", None, None),
    "TaskerAgent": ("oagi.agent.tasker", None, None),
    "AsyncAgentObserver": ("oagi.agent.observer.agent_observer", None, None),
    # Server modules (require server dependencies)
    "create_app": ("oagi.server.main", "socketio", "server"),
    "ServerConfig": ("oagi.server.config", "pydantic_settings", "server"),
    "sio": ("oagi.server.socketio_server", "socketio", "server"),
    # Wayland handlers
    "AsyncYdotoolActionHandler": (
        "oagi.handler.async_ydotool_action_handler",
        "screeninfo",
        "desktop",
    ),
    "YdotoolActionHandler": (
        "oagi.handler.ydotool_action_handler",
        "screeninfo",
        "desktop",
    ),
    "YdotoolConfig": (
        "oagi.handler.ydotool_action_handler",
        "screeninfo",
        "desktop",
    ),
    "ScreenManager": ("oagi.handler.screen_manager", None, None),
}

if TYPE_CHECKING:
    from oagi.agent.default import AsyncDefaultAgent
    from oagi.agent.observer.agent_observer import AsyncAgentObserver
    from oagi.agent.tasker import TaskerAgent
    from oagi.converters.base import BaseActionConverter
    from oagi.converters.pyautogui_action_converter import PyautoguiActionConvertor
    from oagi.handler.async_pyautogui_action_handler import AsyncPyautoguiActionHandler
    from oagi.handler.async_screenshot_maker import AsyncScreenshotMaker
    from oagi.handler.async_ydotool_action_handler import AsyncYdotoolActionHandler
    from oagi.handler.pil_image import PILImage
    from oagi.handler.pyautogui_action_handler import PyautoguiActionHandler
    from oagi.handler.screen_manager import ScreenManager
    from oagi.handler.screenshot_maker import ScreenshotMaker
    from oagi.handler.utils import PyautoguiConfig
    from oagi.handler.ydotool_action_handler import YdotoolActionHandler, YdotoolConfig
    from oagi.server.config import ServerConfig
    from oagi.server.main import create_app
    from oagi.server.socketio_server import sio


def __getattr__(name: str):
    """Lazy import for optional dependency modules with helpful error messages."""
    if name in _LAZY_IMPORTS_DATA:
        module_path, package, extra = _LAZY_IMPORTS_DATA[name]
        if package is not None:
            check_optional_dependency(package, name, extra)
        module = importlib.import_module(module_path)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Return all public names including lazy imports."""
    return sorted(set(globals().keys()) | set(_LAZY_IMPORTS_DATA.keys()))


__all__ = [
    # Version
    "__version__",
    # Core sync classes
    "Actor",
    "AsyncActor",
    "Task",  # Deprecated: Use Actor instead
    "ShortTask",  # Deprecated
    "SyncClient",
    # Core async classes
    "AsyncTask",  # Deprecated: Use AsyncActor instead
    "AsyncShortTask",  # Deprecated
    "AsyncClient",
    # Agent classes
    "AsyncDefaultAgent",
    "TaskerAgent",
    "AsyncAgentObserver",
    # Configuration
    "ImageConfig",
    # Response models
    "GenerateResponse",
    "UploadFileResponse",
    "ErrorResponse",
    "ErrorDetail",
    # Exceptions
    "OAGIError",
    "APIError",
    "AuthenticationError",
    "ConfigurationError",
    "NetworkError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "RequestTimeoutError",
    "ValidationError",
    # Lazy imports - Image classes
    "PILImage",
    # Lazy imports - Handler classes
    "PyautoguiActionHandler",
    "PyautoguiConfig",
    "ScreenshotMaker",
    # Lazy imports - Async handler classes
    "AsyncPyautoguiActionHandler",
    "AsyncScreenshotMaker",
    # Lazy imports - Server modules (optional)
    "create_app",
    "ServerConfig",
    "sio",
    # Lazy imports - Wayland handler classes
    "AsyncYdotoolActionHandler",
    "YdotoolActionHandler",
    "YdotoolConfig",
    # Lazy imports - Screen manager
    "ScreenManager",
    # Lazy imports - Action converters
    "PyautoguiActionConvertor",
    "BaseActionConverter",
]
