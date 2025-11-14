# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
import importlib

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
)
from oagi.task import Actor, AsyncActor, AsyncShortTask, AsyncTask, ShortTask, Task
from oagi.types import (
    AsyncActionHandler,
    AsyncImageProvider,
    ImageConfig,
)
from oagi.types.models import ErrorDetail, ErrorResponse, LLMResponse

# Lazy imports for pyautogui-dependent modules
# These will only be imported when actually accessed
_LAZY_IMPORTS = {
    "AsyncPyautoguiActionHandler": "oagi.handler.async_pyautogui_action_handler",
    "AsyncScreenshotMaker": "oagi.handler.async_screenshot_maker",
    "PILImage": "oagi.handler.pil_image",
    "PyautoguiActionHandler": "oagi.handler.pyautogui_action_handler",
    "PyautoguiConfig": "oagi.handler.pyautogui_action_handler",
    "ScreenshotMaker": "oagi.handler.screenshot_maker",
    # Agent modules (to avoid circular imports)
    "TaskerAgent": "oagi.agent.tasker",
    # Server modules (optional - requires server dependencies)
    "create_app": "oagi.server.main",
    "ServerConfig": "oagi.server.config",
    "sio": "oagi.server.socketio_server",
}


def __getattr__(name: str):
    """Lazy import for pyautogui-dependent modules."""
    if name in _LAZY_IMPORTS:
        module_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_name)
        return getattr(module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
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
    "TaskerAgent",
    # Async protocols
    "AsyncActionHandler",
    "AsyncImageProvider",
    # Configuration
    "ImageConfig",
    # Response models
    "LLMResponse",
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
    # Lazy imports
    # Image classes
    "PILImage",
    # Handler classes
    "PyautoguiActionHandler",
    "PyautoguiConfig",
    "ScreenshotMaker",
    # Async handler classes
    "AsyncPyautoguiActionHandler",
    "AsyncScreenshotMaker",
    # Server modules (optional)
    "create_app",
    "ServerConfig",
    "sio",
]
