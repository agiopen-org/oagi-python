# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
import importlib

from oagi.async_single_step import async_single_step
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
from oagi.single_step import single_step
from oagi.task import AsyncShortTask, AsyncTask, ShortTask, Task
from oagi.types import (
    AsyncActionHandler,
    AsyncImageProvider,
    ImageConfig,
)
from oagi.types.models import ErrorDetail, ErrorResponse, LLMResponse

# Lazy imports for pyautogui-dependent modules
# These will only be imported when actually accessed
_LAZY_IMPORTS = {
    "AsyncPyautoguiActionHandler": "oagi.async_pyautogui_action_handler",
    "AsyncScreenshotMaker": "oagi.async_screenshot_maker",
    "PILImage": "oagi.pil_image",
    "PyautoguiActionHandler": "oagi.pyautogui_action_handler",
    "PyautoguiConfig": "oagi.pyautogui_action_handler",
    "ScreenshotMaker": "oagi.screenshot_maker",
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
    "Task",
    "ShortTask",
    "SyncClient",
    # Core async classes
    "AsyncTask",
    "AsyncShortTask",
    "AsyncClient",
    # Agent classes
    "TaskerAgent",
    # Functions
    "single_step",
    "async_single_step",
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
