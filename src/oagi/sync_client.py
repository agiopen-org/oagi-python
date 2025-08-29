# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import base64
import os
from typing import Optional

import httpx
from pydantic import BaseModel

from .logging import get_logger
from .types import Action

logger = get_logger("sync_client")


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


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
    reason: str | None
    usage: Usage


class ErrorResponse(BaseModel):
    error: str
    message: str
    code: int


class SyncClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        # Get from environment if not provided
        self.base_url = base_url or os.getenv("OAGI_BASE_URL")
        self.api_key = api_key or os.getenv("OAGI_API_KEY")

        # Validate required configuration
        if not self.base_url:
            raise ValueError(
                "OAGI base URL must be provided either as 'base_url' parameter or "
                "OAGI_BASE_URL environment variable"
            )

        if not self.api_key:
            raise ValueError(
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

    def create_message(
        self,
        model: str,
        screenshot: str,  # base64 encoded
        task_description: Optional[str] = None,
        task_id: Optional[str] = None,
        max_actions: Optional[int] = 5,
        api_version: Optional[str] = None,
    ) -> LLMResponse:
        """
        Call the /v1/message endpoint to analyze task and screenshot

        Args:
            model: The model to use for task analysis
            screenshot: Base64-encoded screenshot image
            task_description: Description of the task (required for new sessions)
            task_id: Task ID for continuing existing task
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
        if max_actions is not None:
            payload["max_actions"] = max_actions

        logger.info(f"Making API request to /v1/message with model: {model}")
        logger.debug(
            f"Request includes task_description: {task_description is not None}, task_id: {task_id is not None}"
        )

        response = self.client.post("/v1/message", json=payload, headers=headers, timeout=self.timeout)

        if response.status_code == 200:
            result = LLMResponse(**response.json())
            logger.info(
                f"API request successful - task_id: {result.task_id}, step: {result.current_step}, complete: {result.is_complete}"
            )
            logger.debug(f"Response included {len(result.actions)} actions")
            return result
        else:
            # Handle error responses
            try:
                error_data = response.json()
                error = ErrorResponse(**error_data)
                logger.error(f"API Error {error.code}: {error.error} - {error.message}")
                raise httpx.HTTPStatusError(
                    f"API Error {error.code}: {error.error} - {error.message}",
                    request=response.request,
                    response=response,
                )
            except ValueError:
                # If response is not JSON, raise generic error
                logger.error(f"Non-JSON API error response: {response.status_code}")
                response.raise_for_status()

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
