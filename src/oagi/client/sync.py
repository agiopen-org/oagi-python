# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from functools import wraps

import httpx
from httpx import Response

from ..exceptions import NetworkError, RequestTimeoutError
from ..logging import get_logger
from ..types.models import LLMResponse
from .base import BaseClient

logger = get_logger("sync_client")


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


class SyncClient(BaseClient[httpx.Client]):
    """Synchronous HTTP client for the OAGI API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        super().__init__(base_url, api_key)
        self.client = httpx.Client(base_url=self.base_url)
        logger.info(f"SyncClient initialized with base_url: {self.base_url}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        """Close the underlying httpx client."""
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
        last_task_id: str | None = None,
        history_steps: int | None = None,
        temperature: float | None = None,
        api_version: str | None = None,
    ) -> "LLMResponse":
        """
        Call the /v1/message endpoint to analyze task and screenshot

        Args:
            model: The model to use for task analysis
            screenshot: Base64-encoded screenshot image
            task_description: Description of the task (required for new sessions)
            task_id: Task ID for continuing existing task
            instruction: Additional instruction when continuing a session (only works with task_id)
            max_actions: Maximum number of actions to return (1-20)
            last_task_id: Previous task ID to retrieve history from (only works with task_id)
            history_steps: Number of historical steps to include from last_task_id (default: 1, max: 10)
            temperature: Sampling temperature (0.0-2.0) for LLM inference
            api_version: API version header

        Returns:
            LLMResponse: The response from the API

        Raises:
            httpx.HTTPStatusError: For HTTP error responses
        """
        headers = self._build_headers(api_version)
        payload = self._build_payload(
            model=model,
            screenshot=screenshot,
            task_description=task_description,
            task_id=task_id,
            instruction=instruction,
            max_actions=max_actions,
            last_task_id=last_task_id,
            history_steps=history_steps,
            temperature=temperature,
        )

        self._log_request_info(model, task_description, task_id)

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

        return self._process_response(response)

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
