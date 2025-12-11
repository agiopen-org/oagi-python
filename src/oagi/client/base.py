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

from ..constants import (
    API_KEY_HELP_URL,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    HTTP_CLIENT_TIMEOUT,
)
from ..exceptions import (
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
from ..logging import get_logger
from ..types.models import (
    ErrorResponse,
    GenerateResponse,
    UploadFileResponse,
    Usage,
)
from ..types.models.step import Step
from ..utils.output_parser import parse_raw_output

logger = get_logger("client.base")

# TypeVar for HTTP client type (httpx.Client or httpx.AsyncClient)
HttpClientT = TypeVar("HttpClientT")


class BaseClient(Generic[HttpClientT]):
    """Base class with shared business logic for sync/async clients."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        # Get from environment if not provided
        self.base_url = base_url or os.getenv("OAGI_BASE_URL") or DEFAULT_BASE_URL
        self.api_key = api_key or os.getenv("OAGI_API_KEY")

        # Validate required configuration
        if not self.api_key:
            raise ConfigurationError(
                "OAGI API key must be provided either as 'api_key' parameter or "
                "OAGI_API_KEY environment variable. "
                f"Get your API key at {API_KEY_HELP_URL}"
            )

        self.base_url = self.base_url.rstrip("/")
        self.timeout = HTTP_CLIENT_TIMEOUT
        self.max_retries = max_retries
        self.client: HttpClientT  # Will be set by subclasses

        logger.info(f"Client initialized with base_url: {self.base_url}")

    def _build_headers(self, api_version: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if api_version:
            headers["x-api-version"] = api_version
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    @staticmethod
    def _log_trace_id(response) -> None:
        """Log trace IDs from response headers for debugging."""
        logger.error(f"Request Id: {response.headers.get('x-request-id', '')}")
        logger.error(f"Trace Id: {response.headers.get('x-trace-id', '')}")

    def _build_chat_completion_kwargs(
        self,
        model: str,
        messages: list,
        temperature: float | None = None,
        task_id: str | None = None,
    ) -> dict:
        """Build kwargs dict for OpenAI chat completion call.

        Args:
            model: Model to use for inference
            messages: Full message history (OpenAI-compatible format)
            temperature: Sampling temperature (0.0-2.0)
            task_id: Optional task ID for multi-turn conversations

        Returns:
            Dict of kwargs for chat.completions.create()
        """
        kwargs: dict = {"model": model, "messages": messages}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if task_id is not None:
            kwargs["extra_body"] = {"task_id": task_id}
        return kwargs

    def _parse_chat_completion_response(
        self, response
    ) -> tuple[Step, str, Usage | None]:
        """Extract and parse OpenAI chat completion response, and log success.

        This is sync/async agnostic as it only processes the response object.

        Args:
            response: OpenAI ChatCompletion response object

        Returns:
            Tuple of (Step, raw_output, Usage)
        """
        raw_output = response.choices[0].message.content or ""
        step = parse_raw_output(raw_output)

        # Extract task_id from response (custom field from OAGI API)
        task_id = getattr(response, "task_id", None)

        usage = None
        if response.usage:
            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        # Log success with task_id and usage
        usage_str = (
            f", tokens: {usage.prompt_tokens}+{usage.completion_tokens}"
            if usage
            else ""
        )
        task_str = f"task_id: {task_id}, " if task_id else ""
        logger.info(
            f"Chat completion successful - {task_str}actions: {len(step.actions)}, "
            f"stop: {step.stop}{usage_str}"
        )

        return step, raw_output, usage

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

    def _process_upload_response(self, response: httpx.Response) -> UploadFileResponse:
        """Process response from /v1/file/upload endpoint.

        Args:
            response: HTTP response from upload endpoint

        Returns:
            UploadFileResponse with presigned URL

        Raises:
            RequestTimeoutError: If request times out
            NetworkError: If network error occurs
            APIError: If API returns error or invalid response
        """
        response_data = self._parse_response_json(response)

        # Check for error status codes first (follows _process_response pattern)
        if response.status_code != 200:
            self._handle_response_error(response, response_data)

        try:
            upload_file_response = UploadFileResponse(**response_data)
            logger.debug("Calling /v1/file/upload successful")
            return upload_file_response
        except Exception as e:
            logger.error(f"Invalid upload response: {response.status_code}")
            raise APIError(
                f"Invalid presigned S3 URL response: {e}",
                status_code=response.status_code,
                response=response,
            )

    def _handle_upload_http_errors(
        self, e: Exception, response: httpx.Response | None = None
    ):
        """Handle HTTP errors during upload request.

        Args:
            e: The exception that occurred
            response: Optional HTTP response

        Raises:
            RequestTimeoutError: If request times out
            NetworkError: If network error occurs
            APIError: For other HTTP errors
        """
        if isinstance(e, httpx.TimeoutException):
            logger.error(f"Request timed out after {self.timeout} seconds")
            raise RequestTimeoutError(
                f"Request timed out after {self.timeout} seconds", e
            )
        elif isinstance(e, httpx.NetworkError):
            logger.error(f"Network error: {e}")
            raise NetworkError(f"Network error: {e}", e)
        elif isinstance(e, httpx.HTTPStatusError) and response:
            logger.warning(f"Invalid status code: {e}")
            exception_class = self._get_exception_class(response.status_code)
            raise exception_class(
                f"API error (status {response.status_code})",
                status_code=response.status_code,
                response=response,
            )
        else:
            raise

    def _handle_s3_upload_error(
        self, e: Exception, response: httpx.Response | None = None
    ):
        """Handle S3 upload errors.

        Args:
            e: The exception that occurred
            response: Optional HTTP response from S3

        Raises:
            APIError: Wrapping the S3 upload error
        """
        logger.error(f"S3 upload failed: {e}")
        status_code = response.status_code if response else 500
        raise APIError(message=str(e), status_code=status_code, response=response)

    def _prepare_worker_request(
        self,
        worker_id: str,
        overall_todo: str,
        task_description: str,
        todos: list[dict],
        history: list[dict] | None = None,
        current_todo_index: int | None = None,
        task_execution_summary: str | None = None,
        current_screenshot: str | None = None,
        current_subtask_instruction: str | None = None,
        window_steps: list[dict] | None = None,
        window_screenshots: list[str] | None = None,
        result_screenshot: str | None = None,
        prior_notes: str | None = None,
        latest_todo_summary: str | None = None,
        api_version: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Prepare worker request with validation, payload, and headers.

        Args:
            worker_id: One of "oagi_first", "oagi_follow", "oagi_task_summary"
            overall_todo: Current todo description
            task_description: Overall task description
            todos: List of todo dicts with index, description, status, execution_summary
            history: List of history dicts with todo_index, todo_description, action_count, summary, completed
            current_todo_index: Index of current todo being executed
            task_execution_summary: Summary of overall task execution
            current_screenshot: Uploaded file UUID for screenshot (oagi_first)
            current_subtask_instruction: Subtask instruction (oagi_follow)
            window_steps: Action steps list (oagi_follow)
            window_screenshots: Uploaded file UUIDs list (oagi_follow)
            result_screenshot: Uploaded file UUID for result screenshot (oagi_follow)
            prior_notes: Execution notes (oagi_follow)
            latest_todo_summary: Latest summary (oagi_task_summary)
            api_version: API version header

        Returns:
            Tuple of (payload dict, headers dict)

        Raises:
            ValueError: If worker_id is invalid
        """
        # Validate worker_id
        valid_workers = {"oagi_first", "oagi_follow", "oagi_task_summary"}
        if worker_id not in valid_workers:
            raise ValueError(
                f"Invalid worker_id '{worker_id}'. Must be one of: {valid_workers}"
            )

        logger.info(f"Calling /v1/generate with worker_id: {worker_id}")

        # Build flattened payload (no oagi_data wrapper)
        payload: dict[str, Any] = {
            "external_worker_id": worker_id,
            "overall_todo": overall_todo,
            "task_description": task_description,
            "todos": todos,
            "history": history or [],
        }

        # Add optional memory fields
        if current_todo_index is not None:
            payload["current_todo_index"] = current_todo_index
        if task_execution_summary is not None:
            payload["task_execution_summary"] = task_execution_summary

        # Add optional screenshot/worker-specific fields
        if current_screenshot is not None:
            payload["current_screenshot"] = current_screenshot
        if current_subtask_instruction is not None:
            payload["current_subtask_instruction"] = current_subtask_instruction
        if window_steps is not None:
            payload["window_steps"] = window_steps
        if window_screenshots is not None:
            payload["window_screenshots"] = window_screenshots
        if result_screenshot is not None:
            payload["result_screenshot"] = result_screenshot
        if prior_notes is not None:
            payload["prior_notes"] = prior_notes
        if latest_todo_summary is not None:
            payload["latest_todo_summary"] = latest_todo_summary

        # Build headers
        headers = self._build_headers(api_version)

        return payload, headers

    def _process_generate_response(self, response: httpx.Response) -> GenerateResponse:
        """Process response from /v1/generate endpoint.

        Args:
            response: HTTP response from generate endpoint

        Returns:
            GenerateResponse with LLM output

        Raises:
            APIError: If API returns error or invalid response
        """
        response_data = self._parse_response_json(response)

        # Check if it's an error response (non-200 status)
        if response.status_code != 200:
            self._handle_response_error(response, response_data)

        # Parse successful response
        result = GenerateResponse(**response_data)

        # Capture request_id from response header
        result.request_id = response.headers.get("X-Request-ID")

        logger.info(
            f"Generate request successful - tokens: {result.prompt_tokens}+{result.completion_tokens}, "
            f"request_id: {result.request_id}"
        )
        return result
