# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from ..client import AsyncClient
from ..logging import get_logger
from ..types import Image, Step
from .base import BaseTask, encode_screenshot_from_bytes

logger = get_logger("async_task")


class AsyncTask(BaseTask):
    """Async base class for task automation with the OAGI API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "vision-model-v1",
        temperature: float | None = None,
    ):
        super().__init__(api_key, base_url, model, temperature)
        self.client = AsyncClient(base_url=base_url, api_key=api_key)
        self.api_key = self.client.api_key
        self.base_url = self.client.base_url

    async def init_task(
        self,
        task_desc: str,
        max_steps: int = 5,
        last_task_id: str | None = None,
        history_steps: int | None = None,
    ):
        """Initialize a new task with the given description.

        Args:
            task_desc: Task description
            max_steps: Maximum number of steps (for logging)
            last_task_id: Previous task ID to retrieve history from
            history_steps: Number of historical steps to include (default: 1)
        """
        self._prepare_init_task(task_desc, last_task_id, history_steps)
        response = await self.client.create_message(
            model=self.model,
            screenshot="",
            task_description=self.task_description,
            task_id=None,
        )
        self._process_init_response(response, task_desc, max_steps, prefix="Async ")

    async def step(
        self,
        screenshot: Image | bytes,
        instruction: str | None = None,
        temperature: float | None = None,
    ) -> Step:
        """Send screenshot to the server and get the next actions.

        Args:
            screenshot: Screenshot as Image object or raw bytes
            instruction: Optional additional instruction for this step (only works with existing task_id)
            temperature: Sampling temperature for this step (overrides task default if provided)

        Returns:
            Step: The actions and reasoning for this step
        """
        self._validate_step_preconditions()
        self._log_step_execution(prefix="async ")

        try:
            # Convert Image to bytes using the protocol
            screenshot_bytes = self._prepare_screenshot(screenshot)
            screenshot_b64 = encode_screenshot_from_bytes(screenshot_bytes)

            # Use provided temperature or fall back to task default
            temp = self._get_temperature(temperature)

            # Call API
            response = await self.client.create_message(
                model=self.model,
                screenshot=screenshot_b64,
                task_description=self.task_description,
                task_id=self.task_id,
                instruction=instruction,
                last_task_id=self.last_task_id if self.task_id else None,
                history_steps=self.history_steps if self.task_id else None,
                temperature=temp,
            )

            # Update task_id from response
            self._update_task_id(response)

            # Convert API response to Step
            return self._build_step_response(response, prefix="Async ")

        except Exception as e:
            logger.error(f"Error during async step execution: {e}")
            raise

    async def close(self):
        """Close the underlying HTTP client to free resources."""
        await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
