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
from ..types.models import LLMResponse, UploadFileResponse
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
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            self._handle_upload_http_errors(e)

        return self._process_response(response)

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
        content: bytes,
    ) -> None:
        """
        Upload image bytes to S3 using presigned URL

        Args:
            url: S3 presigned URL
            content: Image bytes to upload

        Raises:
            APIError: If upload fails
        """
        logger.debug("Async uploading image to S3")
        try:
            response = await self.upload_client.put(url=url, content=content)
            response.raise_for_status()
        except Exception as e:
            self._handle_s3_upload_error(e, response)

    async def put_s3_presigned_url(
        self,
        screenshot: bytes,
        api_version: str | None = None,
    ) -> UploadFileResponse:
        """
        Get S3 presigned URL and upload image (convenience method)

        Args:
            screenshot: Screenshot image bytes
            api_version: API version header

        Returns:
            UploadFileResponse: The response from /v1/file/upload with uuid and presigned S3 URL
        """
        upload_file_response = await self.get_s3_presigned_url(api_version)
        await self.upload_to_s3(upload_file_response.url, screenshot)
        return upload_file_response
