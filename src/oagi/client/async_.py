# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from functools import wraps

import httpx

from ..logging import get_logger
from ..types import Image
from ..types.models import GenerateResponse, LLMResponse, UploadFileResponse
from .base import BaseClient

logger = get_logger("async_client")


def async_log_trace_on_failure(func):
    """Async decorator that logs trace ID when a method fails."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Try to get response from the exception if it has one
            if (response := getattr(e, "response", None)) is not None:
                logger.error(f"Request Id: {response.headers.get('x-request-id', '')}")
                logger.error(f"Trace Id: {response.headers.get('x-trace-id', '')}")
            raise

    return wrapper


class AsyncClient(BaseClient[httpx.AsyncClient]):
    """Asynchronous HTTP client for the OAGI API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        super().__init__(base_url, api_key)
        self.client = httpx.AsyncClient(base_url=self.base_url)
        self.upload_client = httpx.AsyncClient(timeout=60)  # client for uploading image
        logger.info(f"AsyncClient initialized with base_url: {self.base_url}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        await self.upload_client.aclose()

    async def close(self):
        """Close the underlying httpx async clients."""
        await self.client.aclose()
        await self.upload_client.aclose()

    @async_log_trace_on_failure
    async def create_message(
        self,
        model: str,
        screenshot: bytes | None = None,
        screenshot_url: str | None = None,
        task_description: str | None = None,
        task_id: str | None = None,
        instruction: str | None = None,
        messages_history: list | None = None,
        temperature: float | None = None,
        api_version: str | None = None,
    ) -> "LLMResponse":
        """
        Call the /v2/message endpoint to analyze task and screenshot

        Args:
            model: The model to use for task analysis
            screenshot: Screenshot image bytes (mutually exclusive with screenshot_url)
            screenshot_url: Direct URL to screenshot (mutually exclusive with screenshot)
            task_description: Description of the task (required for new sessions)
            task_id: Task ID for continuing existing task
            instruction: Additional instruction when continuing a session
            messages_history: OpenAI-compatible chat message history
            temperature: Sampling temperature (0.0-2.0) for LLM inference
            api_version: API version header

        Returns:
            LLMResponse: The response from the API

        Raises:
            ValueError: If both or neither screenshot and screenshot_url are provided
            httpx.HTTPStatusError: For HTTP error responses
        """
        # Validate that exactly one is provided
        if (screenshot is None) == (screenshot_url is None):
            raise ValueError(
                "Exactly one of 'screenshot' or 'screenshot_url' must be provided"
            )

        self._log_request_info(model, task_description, task_id)

        # Upload screenshot to S3 if bytes provided, otherwise use URL directly
        upload_file_response = None
        if screenshot is not None:
            upload_file_response = await self.put_s3_presigned_url(
                screenshot, api_version
            )

        # Prepare message payload
        headers, payload = self._prepare_message_payload(
            model=model,
            upload_file_response=upload_file_response,
            task_description=task_description,
            task_id=task_id,
            instruction=instruction,
            messages_history=messages_history,
            temperature=temperature,
            api_version=api_version,
            screenshot_url=screenshot_url,
        )

        # Make request
        try:
            response = await self.client.post(
                "/v2/message", json=payload, headers=headers, timeout=self.timeout
            )
            return self._process_response(response)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            self._handle_upload_http_errors(e)

    async def health_check(self) -> dict:
        """
        Call the /health endpoint for health check

        Returns:
            dict: Health check response
        """
        logger.debug("Making async health check request")
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            result = response.json()
            logger.debug("Async health check successful")
            return result
        except httpx.HTTPStatusError as e:
            logger.warning(f"Async health check failed: {e}")
            raise

    async def get_s3_presigned_url(
        self,
        api_version: str | None = None,
    ) -> UploadFileResponse:
        """
        Call the /v1/file/upload endpoint to get a S3 presigned URL

        Args:
            api_version: API version header

        Returns:
            UploadFileResponse: The response from /v1/file/upload with uuid and presigned S3 URL
        """
        logger.debug("Making async API request to /v1/file/upload")

        try:
            headers = self._build_headers(api_version)
            response = await self.client.get(
                "/v1/file/upload", headers=headers, timeout=self.timeout
            )
            return self._process_upload_response(response)
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
            self._handle_upload_http_errors(e, getattr(e, "response", None))

    async def upload_to_s3(
        self,
        url: str,
        content: bytes | Image,
    ) -> None:
        """
        Upload image bytes to S3 using presigned URL

        Args:
            url: S3 presigned URL
            content: Image bytes or Image object to upload

        Raises:
            APIError: If upload fails
        """
        logger.debug("Async uploading image to S3")

        # Convert Image to bytes if needed
        if isinstance(content, Image):
            content = content.read()

        response = None
        try:
            response = await self.upload_client.put(url=url, content=content)
            response.raise_for_status()
        except Exception as e:
            self._handle_s3_upload_error(e, response)

    async def put_s3_presigned_url(
        self,
        screenshot: bytes | Image,
        api_version: str | None = None,
    ) -> UploadFileResponse:
        """
        Get S3 presigned URL and upload image (convenience method)

        Args:
            screenshot: Screenshot image bytes or Image object
            api_version: API version header

        Returns:
            UploadFileResponse: The response from /v1/file/upload with uuid and presigned S3 URL
        """
        upload_file_response = await self.get_s3_presigned_url(api_version)
        await self.upload_to_s3(upload_file_response.url, screenshot)
        return upload_file_response

    @async_log_trace_on_failure
    async def call_worker(
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
    ) -> GenerateResponse:
        """Call the /v1/generate endpoint for OAGI worker processing.

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
            GenerateResponse with LLM output and usage stats

        Raises:
            ValueError: If worker_id is invalid
            APIError: If API returns error
        """
        # Prepare request (validation, payload, headers)
        payload, headers = self._prepare_worker_request(
            worker_id=worker_id,
            overall_todo=overall_todo,
            task_description=task_description,
            todos=todos,
            deliverables=deliverables,
            history=history,
            current_todo_index=current_todo_index,
            task_execution_summary=task_execution_summary,
            current_screenshot=current_screenshot,
            current_subtask_instruction=current_subtask_instruction,
            window_steps=window_steps,
            window_screenshots=window_screenshots,
            result_screenshot=result_screenshot,
            prior_notes=prior_notes,
            latest_todo_summary=latest_todo_summary,
            api_version=api_version,
        )

        # Make request
        try:
            response = await self.client.post(
                "/v1/generate", json=payload, headers=headers, timeout=self.timeout
            )
            return self._process_generate_response(response)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            self._handle_upload_http_errors(e)
