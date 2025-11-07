# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from functools import wraps

import httpx

from ..exceptions import APIError, NetworkError, RequestTimeoutError
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
        screenshot: bytes,
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
            screenshot: Screenshot image bytes
            task_description: Description of the task (required for new sessions)
            task_id: Task ID for continuing existing task
            instruction: Additional instruction when continuing a session
            messages_history: OpenAI-compatible chat message history
            temperature: Sampling temperature (0.0-2.0) for LLM inference
            api_version: API version header

        Returns:
            LLMResponse: The response from the API

        Raises:
            httpx.HTTPStatusError: For HTTP error responses
        """
        self._log_request_info(model, task_description, task_id)

        # Upload screenshot to S3 and get URL
        upload_file_response = await self.put_s3_presigned_url(screenshot, api_version)
        screenshot_url = upload_file_response.download_url

        # Build user message with screenshot
        if messages_history is None:
            messages_history = []

        content = [{"type": "image_url", "image_url": {"url": screenshot_url}}]
        if instruction:
            content.append({"type": "text", "text": instruction})

        user_message = {"role": "user", "content": content}
        messages_history.append(user_message)

        # Build payload
        headers = self._build_headers(api_version)
        payload = self._build_payload(
            model=model,
            messages_history=messages_history,
            task_description=task_description,
            task_id=task_id,
            temperature=temperature,
        )

        try:
            response = await self.client.post(
                "/v2/message", json=payload, headers=headers, timeout=self.timeout
            )
        except httpx.TimeoutException as e:
            logger.error(f"Async request timed out after {self.timeout} seconds")
            raise RequestTimeoutError(
                f"Request timed out after {self.timeout} seconds", e
            )
        except httpx.NetworkError as e:
            logger.error(f"Async network error: {e}")
            raise NetworkError(f"Network error: {e}", e)

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

    async def put_s3_presigned_url(
        self,
        screenshot: bytes,
        api_version: str | None = None,
    ) -> UploadFileResponse:
        """
        Call the /v1/file/upload endpoint to fetch a S3 presigned URL and upload image

        Args:
            screenshot: Screenshot image bytes
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
            response_data = response.json()
            upload_file_response = UploadFileResponse(**response_data)
            logger.debug("Async calling /v1/file/upload successful")
        except httpx.TimeoutException as e:
            logger.error(f"Async request timed out after {self.timeout} seconds")
            raise RequestTimeoutError(
                f"Request timed out after {self.timeout} seconds", e
            )
        except httpx.NetworkError as e:
            logger.error(f"Async network error: {e}")
            raise NetworkError(f"Network error: {e}", e)
        except httpx.HTTPStatusError as e:
            logger.warning(f"Async invalid status code: {e}")
            exception_class = self._get_exception_class(response.status_code)
            raise exception_class(
                f"API error (status {response.status_code})",
                status_code=response.status_code,
                response=response,
            )
        except ValueError:
            logger.error(f"Async non-JSON API response: {response.status_code}")
            raise APIError(
                f"Invalid response format (status {response.status_code})",
                status_code=response.status_code,
                response=response,
            )
        except KeyError:
            logger.error(f"Async invalid response: {response.status_code}")
            raise APIError(
                f"Invalid presigned S3 URL (result {response_data})",
                status_code=response.status_code,
                response=response,
            )

        logger.debug("Async uploading image to S3")
        try:
            response = await self.upload_client.put(
                url=upload_file_response.url, content=screenshot
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Async S3 upload failed: {e}")
            raise APIError(
                message=str(e), status_code=response.status_code, response=response
            )
        return upload_file_response
