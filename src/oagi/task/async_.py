# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import warnings

from ..client import AsyncClient
from ..logging import get_logger
from ..types import Image, Step
from .base import BaseTask

logger = get_logger("async_task")


class AsyncActor(BaseTask):
    """Async base class for task automation with the OAGI API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-actor-1",
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
    ):
        """Initialize a new task with the given description.

        Args:
            task_desc: Task description
            max_steps: Maximum number of steps (for logging)
        """
        self._prepare_init_task(task_desc, max_steps)

    async def step(
        self,
        screenshot: Image | bytes,
        instruction: str | None = None,
        temperature: float | None = None,
    ) -> Step:
        """Send screenshot to the server and get the next actions.

        Args:
            screenshot: Screenshot as Image object or raw bytes
            instruction: Optional additional instruction for this step
            temperature: Sampling temperature for this step (overrides task default if provided)

        Returns:
            Step: The actions and reasoning for this step
        """
        self._validate_step_preconditions()
        self._log_step_execution(prefix="async ")

        try:
            # Use provided temperature or fall back to task default
            temp = self._get_temperature(temperature)

            # Prepare screenshot kwargs (handles URLImage vs bytes/Image)
            screenshot_kwargs = self._prepare_screenshot_kwargs(screenshot)

            # Call API with dynamically determined screenshot argument
            response = await self.client.create_message(
                model=self.model,
                task_description=self.task_description,
                task_id=self.task_id,
                instruction=instruction,
                messages_history=self.message_history,
                temperature=temp,
                **screenshot_kwargs,
            )

            # Convert API response to Step (also updates message_history)
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


class AsyncTask(AsyncActor):
    """Deprecated: Use AsyncActor instead.

    This class is deprecated and will be removed in a future version.
    Please use AsyncActor instead.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-actor-1",
        temperature: float | None = None,
    ):
        warnings.warn(
            "AsyncTask is deprecated and will be removed in a future version. "
            "Please use AsyncActor instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(api_key, base_url, model, temperature)
