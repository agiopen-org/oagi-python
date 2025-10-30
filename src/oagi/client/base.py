# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import os
from typing import Any, Generic, TypeVar

import httpx

from ..exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from ..logging import get_logger
from ..types.models import ErrorResponse, LLMResponse

logger = get_logger("client.base")

# TypeVar for HTTP client type (httpx.Client or httpx.AsyncClient)
HttpClientT = TypeVar("HttpClientT")


class BaseClient(Generic[HttpClientT]):
    """Base class with shared business logic for sync/async clients."""

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
        self.timeout = 60
        self.client: HttpClientT  # Will be set by subclasses

        logger.info(f"Client initialized with base_url: {self.base_url}")

    def _build_headers(self, api_version: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if api_version:
            headers["x-api-version"] = api_version
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _build_payload(
        self,
        model: str,
        screenshot: str,
        task_description: str | None = None,
        task_id: str | None = None,
        instruction: str | None = None,
        max_actions: int | None = None,
        last_task_id: str | None = None,
        history_steps: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "screenshot": screenshot}

        if task_description is not None:
            payload["task_description"] = task_description
        if task_id is not None:
            payload["task_id"] = task_id
        if instruction is not None:
            payload["instruction"] = instruction
        if max_actions is not None:
            payload["max_actions"] = max_actions
        if last_task_id is not None:
            payload["last_task_id"] = last_task_id
        if history_steps is not None:
            payload["history_steps"] = history_steps
        if temperature is not None:
            payload["sampling_params"] = {"temperature": temperature}

        return payload

    def _handle_response_error(
        self, response: httpx.Response, response_data: dict
    ) -> None:
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
            logger.error(f"API error response without details: {response.status_code}")
            exception_class = self._get_exception_class(response.status_code)
            raise exception_class(
                f"API error (status {response.status_code})",
                status_code=response.status_code,
                response=response,
            )

    def _get_exception_class(self, status_code: int) -> type[APIError]:
        status_map = {
            401: AuthenticationError,
            404: NotFoundError,
            422: ValidationError,
            429: RateLimitError,
        }

        if status_code >= 500:
            return ServerError

        return status_map.get(status_code, APIError)

    def _log_request_info(self, model: str, task_description: Any, task_id: Any):
        logger.info(f"Making API request to /v1/message with model: {model}")
        logger.debug(
            f"Request includes task_description: {task_description is not None}, "
            f"task_id: {task_id is not None}"
        )

    def _parse_response_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError:
            logger.error(f"Non-JSON API response: {response.status_code}")
            raise APIError(
                f"Invalid response format (status {response.status_code})",
                status_code=response.status_code,
                response=response,
            )

    def _process_response(self, response: httpx.Response) -> Any:
        response_data = self._parse_response_json(response)

        # Check if it's an error response (non-200 status)
        if response.status_code != 200:
            self._handle_response_error(response, response_data)

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
            f"API request successful - task_id: {result.task_id}, "
            f"step: {result.current_step}, complete: {result.is_complete}"
        )
        logger.debug(f"Response included {len(result.actions)} actions")
        return result
