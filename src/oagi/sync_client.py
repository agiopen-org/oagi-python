# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import base64
import os
from functools import wraps

import httpx
from httpx import Response
from pydantic import BaseModel

from .exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RequestTimeoutError,
    ServerError,
    ValidationError,
)
from .logging import get_logger
from .types import Action

logger = get_logger("sync_client")


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorDetail | None


class LLMResponse(BaseModel):
    id: str
    task_id: str
    object: str = "task.completion"
    created: int
    model: str
    task_description: str
    current_step: int
    is_complete: bool
    actions: list[Action]
    reason: str | None = None
    usage: Usage
    error: ErrorDetail | None = None


def _log_trace_id(response: Response):
    logger.error(f"Request Id: {response.headers.get('x-request-id', '')}")
    logger.error(f"Trace Id: {response.headers.get('x-trace-id', '')}")


def log_trace_on_failure(func):
    """Decorator that logs trace ID when a method fails."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Try to get response from the exception if it has one
            if (response := getattr(e, "response", None)) is not None:
                _log_trace_id(response)
            raise

    return wrapper


class SyncClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        # Get from environment if not provided
        self.base_url = base_url or os.getenv("OAGI_BASE_URL")
        self.api_key = api_key or os.getenv("OAGI_API_KEY")

        # Validate required configuration
        if not self.base_url:
            raise ConfigurationError(
                "OAGI base URL must be provided either as 'base_url' parameter or "
                "OAGI_BASE_URL environment variable"
            )

        if not self.api_key:
            raise ConfigurationError(
                "OAGI API key must be provided either as 'api_key' parameter or "
                "OAGI_API_KEY environment variable"
            )

        self.base_url = self.base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url)
        self.timeout = 60

        logger.info(f"SyncClient initialized with base_url: {self.base_url}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        """Close the underlying httpx client"""
        self.client.close()

    @log_trace_on_failure
    def create_message(
        self,
        model: str,
        screenshot: str,  # base64 encoded
        task_description: str | None = None,
        task_id: str | None = None,
        instruction: str | None = None,
        max_actions: int | None = 5,
        api_version: str | None = None,
    ) -> LLMResponse:
        """
        Call the /v1/message endpoint to analyze task and screenshot

        Args:
            model: The model to use for task analysis
            screenshot: Base64-encoded screenshot image
            task_description: Description of the task (required for new sessions)
            task_id: Task ID for continuing existing task
            instruction: Additional instruction when continuing a session (only works with task_id)
            max_actions: Maximum number of actions to return (1-20)
            api_version: API version header

        Returns:
            LLMResponse: The response from the API

        Raises:
            httpx.HTTPStatusError: For HTTP error responses
        """
        headers = {}
        if api_version:
            headers["x-api-version"] = api_version
        if self.api_key:
            headers["x-api-key"] = self.api_key

        payload = {"model": model, "screenshot": screenshot}

        if task_description is not None:
            payload["task_description"] = task_description
        if task_id is not None:
            payload["task_id"] = task_id
        if instruction is not None:
            payload["instruction"] = instruction
        if max_actions is not None:
            payload["max_actions"] = max_actions

        logger.info(f"Making API request to /v1/message with model: {model}")
        logger.debug(
            f"Request includes task_description: {task_description is not None}, task_id: {task_id is not None}"
        )

        try:
            response = self.client.post(
                "/v1/message", json=payload, headers=headers, timeout=self.timeout
            )
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out after {self.timeout} seconds")
            raise RequestTimeoutError(
                f"Request timed out after {self.timeout} seconds", e
            )
        except httpx.NetworkError as e:
            logger.error(f"Network error: {e}")
            raise NetworkError(f"Network error: {e}", e)

        try:
            response_data = response.json()
        except ValueError:
            # If response is not JSON, raise API error
            logger.error(f"Non-JSON API response: {response.status_code}")
            raise APIError(
                f"Invalid response format (status {response.status_code})",
                status_code=response.status_code,
                response=response,
            )

        # Check if it's an error response (non-200 status or has error field)
        if response.status_code != 200:
            error_resp = ErrorResponse(**response_data)
            if error_resp.error:
                error_code = error_resp.error.code
                error_msg = error_resp.error.message
                logger.error(f"API Error [{error_code}]: {error_msg}")

                # Map to specific exception types based on status code
                exception_class = self._get_exception_class(response.status_code)
                raise exception_class(
                    error_msg,
                    code=error_code,
                    status_code=response.status_code,
                    response=response,
                )
            else:
                # Error response without error details
                logger.error(
                    f"API error response without details: {response.status_code}"
                )
                exception_class = self._get_exception_class(response.status_code)
                raise exception_class(
                    f"API error (status {response.status_code})",
                    status_code=response.status_code,
                    response=response,
                )

        # Parse successful response
        result = LLMResponse(**response_data)

        # Check if the response contains an error (even with 200 status)
        if result.error:
            logger.error(
                f"API Error in response: [{result.error.code}]: {result.error.message}"
            )
            raise APIError(
                result.error.message,
                code=result.error.code,
                status_code=200,
                response=response,
            )

        logger.info(
            f"API request successful - task_id: {result.task_id}, step: {result.current_step}, complete: {result.is_complete}"
        )
        logger.debug(f"Response included {len(result.actions)} actions")
        return result

    def _get_exception_class(self, status_code: int) -> type[APIError]:
        """Get the appropriate exception class based on status code."""
        status_map = {
            401: AuthenticationError,
            404: NotFoundError,
            422: ValidationError,
            429: RateLimitError,
        }

        if status_code >= 500:
            return ServerError

        return status_map.get(status_code, APIError)

    def health_check(self) -> dict:
        """
        Call the /health endpoint for health check

        Returns:
            dict: Health check response
        """
        logger.debug("Making health check request")
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            result = response.json()
            logger.debug("Health check successful")
            return result
        except httpx.HTTPStatusError as e:
            logger.warning(f"Health check failed: {e}")
            raise


def encode_screenshot_from_bytes(image_bytes: bytes) -> str:
    """Helper function to encode image bytes to base64 string"""
    return base64.b64encode(image_bytes).decode("utf-8")


def encode_screenshot_from_file(image_path: str) -> str:
    """Helper function to encode image file to base64 string"""
    with open(image_path, "rb") as f:
        return encode_screenshot_from_bytes(f.read())
