# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

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
