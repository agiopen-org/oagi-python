# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import importlib.util

import httpx


class OAGIError(Exception):
    pass


class APIError(OAGIError):
    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int | None = None,
        response: httpx.Response | None = None,
    ):
        """Initialize APIError.

        Args:
            message: Human-readable error message
            code: API error code for programmatic handling
            status_code: HTTP status code
            response: Original HTTP response object
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.response = response

    def __str__(self) -> str:
        if self.code:
            return f"API Error [{self.code}]: {self.message}"
        return f"API Error: {self.message}"


class AuthenticationError(APIError):
    pass


class RateLimitError(APIError):
    pass


class ValidationError(APIError):
    pass


class NotFoundError(APIError):
    pass


class ServerError(APIError):
    pass


class NetworkError(OAGIError):
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class RequestTimeoutError(NetworkError):
    pass


class ConfigurationError(OAGIError):
    pass


def check_optional_dependency(
    name: str,
    feature: str,
    extra: str,
    raise_error: bool = True,
) -> bool:
    """Check if an optional dependency is available, raise helpful error if not.

    This function validates that an optional dependency is installed without
    returning the module, allowing the caller to use a regular import statement
    afterward. This preserves IDE features like type hints, autocomplete, and
    go-to-definition.

    Args:
        name: Module name to check (e.g., "pyautogui", "PIL")
        feature: Feature name for error message (e.g., "PyautoguiActionHandler")
        extra: extras_require key (e.g., "desktop", "server")
        raise_error: Whether to raise an ImportError if the module is not installed

    Raises:
        ImportError: If the module is not installed, with installation instructions

    Example:
        >>> check_optional_dependency("pyautogui", "PyautoguiActionHandler", "desktop")
        >>> import pyautogui  # Full IDE support: types, autocomplete, navigation
        >>> pyautogui.click(100, 100)
    """
    spec = importlib.util.find_spec(name)
    if spec is not None:
        return True

    msg = (
        f"{feature} requires {extra} dependencies. "
        f"Install with: pip install oagi[{extra}]"
    )
    if raise_error:
        raise ImportError(msg)
    else:
        return False
