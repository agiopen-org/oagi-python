# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from functools import wraps

import httpx
from httpx import AsyncHTTPTransport
from openai import AsyncOpenAI

from ..constants import (
    API_V1_FILE_UPLOAD_ENDPOINT,
    API_V1_GENERATE_ENDPOINT,
    DEFAULT_MAX_RETRIES,
    HTTP_CLIENT_TIMEOUT,
)
from ..logging import get_logger
from ..platform_info import get_sdk_headers
from ..types import Image
from ..types.models import GenerateResponse, UploadFileResponse, Usage
from ..types.models.step import Step
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
                BaseClient._log_trace_id(response)
            raise

    return wrapper


class AsyncClient(BaseClient[httpx.AsyncClient]):
    """Asynchronous HTTP client for the OAGI API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        super().__init__(base_url, api_key, max_retries)

        # Get SDK headers for all clients
        sdk_headers = get_sdk_headers()

        # OpenAI client for chat completions (with retries)
        self.openai_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=f"{self.base_url}/v1",
            max_retries=self.max_retries,
            default_headers=sdk_headers,
        )

        # httpx clients for S3 uploads and other endpoints (with retries)
        transport = AsyncHTTPTransport(retries=self.max_retries)
        self.http_client = httpx.AsyncClient(
            transport=transport, base_url=self.base_url, headers=sdk_headers
        )
        self.upload_client = httpx.AsyncClient(
            transport=transport, timeout=HTTP_CLIENT_TIMEOUT
        )

        logger.info(f"AsyncClient initialized with base_url: {self.base_url}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the underlying async clients."""
        await self.openai_client.close()
        await self.http_client.aclose()
        await self.upload_client.aclose()

    async def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float | None = None,
        task_id: str | None = None,
    ) -> tuple[Step, str, Usage | None]:
        """
        Call OpenAI-compatible /v1/chat/completions endpoint.

        Args:
            model: Model to use for inference
            messages: Full message history (OpenAI-compatible format)
            temperature: Sampling temperature (0.0-2.0)
            task_id: Optional task ID for multi-turn conversations

        Returns:
            Tuple of (Step, raw_output, Usage)
            - Step: Parsed actions and reasoning
            - raw_output: Raw model output string (for message history)
            - Usage: Token usage statistics (or None if not available)
        """
        logger.info(f"Making async chat completion request with model: {model}")
        kwargs = self._build_chat_completion_kwargs(
            model, messages, temperature, task_id
        )
        response = await self.openai_client.chat.completions.create(**kwargs)
        return self._parse_chat_completion_response(response)

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
        logger.debug(f"Making async API request to {API_V1_FILE_UPLOAD_ENDPOINT}")

        try:
            headers = self._build_headers(api_version)
            response = await self.http_client.get(
                API_V1_FILE_UPLOAD_ENDPOINT, headers=headers, timeout=self.timeout
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
            response = await self.http_client.post(
                API_V1_GENERATE_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            return self._process_generate_response(response)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            self._handle_upload_http_errors(e)
