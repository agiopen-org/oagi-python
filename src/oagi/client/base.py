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
    LLMResponse,
    UploadFileResponse,
)

logger = get_logger("client.base")

# TypeVar for HTTP client type (httpx.Client or httpx.AsyncClient)
HttpClientT = TypeVar("HttpClientT")


class BaseClient(Generic[HttpClientT]):
    """Base class with shared business logic for sync/async clients."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        # Get from environment if not provided
        self.base_url = (
            base_url or os.getenv("OAGI_BASE_URL") or "https://api.agiopen.org"
        )
        self.api_key = api_key or os.getenv("OAGI_API_KEY")

        # Validate required configuration
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
        messages_history: list,
        task_description: str | None = None,
        task_id: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Build OpenAI-compatible request payload.

        Args:
            model: Model to use
            messages_history: OpenAI-compatible message history
            task_description: Task description
            task_id: Task ID for continuing session
            temperature: Sampling temperature

        Returns:
            OpenAI-compatible request payload
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages_history,
        }

        if task_description is not None:
            payload["task_description"] = task_description
        if task_id is not None:
            payload["task_id"] = task_id
        if temperature is not None:
            payload["temperature"] = temperature

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
        logger.info(f"Making API request to /v2/message with model: {model}")
        logger.debug(
            f"Request includes task_description: {task_description is not None}, "
            f"task_id: {task_id is not None}"
        )

    def _build_user_message(
        self, screenshot_url: str, instruction: str | None
    ) -> dict[str, Any]:
        """Build OpenAI-compatible user message with screenshot and optional instruction.

        Args:
            screenshot_url: URL of uploaded screenshot
            instruction: Optional text instruction

        Returns:
            User message dict
        """
        content = [{"type": "image_url", "image_url": {"url": screenshot_url}}]
        if instruction:
            content.append({"type": "text", "text": instruction})
        return {"role": "user", "content": content}

    def _prepare_message_payload(
        self,
        model: str,
        upload_file_response: UploadFileResponse | None,
        task_description: str | None,
        task_id: str | None,
        instruction: str | None,
        messages_history: list | None,
        temperature: float | None,
        api_version: str | None,
        screenshot_url: str | None = None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Prepare headers and payload for /v2/message request.

        Args:
            model: Model to use
            upload_file_response: Response from S3 upload (if screenshot was uploaded)
            task_description: Task description
            task_id: Task ID
            instruction: Optional instruction
            messages_history: Message history
            temperature: Sampling temperature
            api_version: API version
            screenshot_url: Direct screenshot URL (alternative to upload_file_response)

        Returns:
            Tuple of (headers, payload)
        """
        # Use provided screenshot_url or get from upload_file_response
        if screenshot_url is None:
            if upload_file_response is None:
                raise ValueError(
                    "Either screenshot_url or upload_file_response must be provided"
                )
            screenshot_url = upload_file_response.download_url

        # Build user message and append to history
        if messages_history is None:
            messages_history = []
        user_message = self._build_user_message(screenshot_url, instruction)
        messages_history.append(user_message)

        # Build payload and headers
        headers = self._build_headers(api_version)
        payload = self._build_payload(
            model=model,
            messages_history=messages_history,
            task_description=task_description,
            task_id=task_id,
            temperature=temperature,
        )

        return headers, payload

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

    def _process_response(self, response: httpx.Response) -> "LLMResponse":
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
            f"complete: {result.is_complete}"
        )
        logger.debug(f"Response included {len(result.actions)} actions")
        return result

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
        try:
            response_data = response.json()
            upload_file_response = UploadFileResponse(**response_data)
            logger.debug("Calling /v1/file/upload successful")
            return upload_file_response
        except ValueError:
            logger.error(f"Non-JSON API response: {response.status_code}")
            raise APIError(
                f"Invalid response format (status {response.status_code})",
                status_code=response.status_code,
                response=response,
            )
        except KeyError as e:
            logger.error(f"Invalid response: {response.status_code}")
            raise APIError(
                f"Invalid presigned S3 URL response: missing field {e}",
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
        deliverables: list[dict],
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
            deliverables: List of deliverable dicts with description, achieved
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
            "deliverables": deliverables,
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

        logger.info(
            f"Generate request successful - tokens: {result.prompt_tokens}+{result.completion_tokens}, "
            f"cost: ${result.cost:.6f}"
        )
        return result
