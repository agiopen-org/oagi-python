# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from .async_client import AsyncClient
from .logging import get_logger
from .sync_client import encode_screenshot_from_bytes
from .types import Image, Step

logger = get_logger("async_task")


class AsyncTask:
    """Async base class for task automation with the OAGI API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "vision-model-v1",
    ):
        self.client = AsyncClient(base_url=base_url, api_key=api_key)
        self.api_key = self.client.api_key
        self.base_url = self.client.base_url
        self.task_id: str | None = None
        self.task_description: str | None = None
        self.model = model

    async def init_task(self, task_desc: str, max_steps: int = 5):
        """Initialize a new task with the given description."""
        self.task_description = task_desc
        response = await self.client.create_message(
            model=self.model,
            screenshot="",
            task_description=self.task_description,
            task_id=None,
        )
        self.task_id = response.task_id  # Reset task_id for new task
        logger.info(f"Async task initialized: '{task_desc}' (max_steps: {max_steps})")

    async def step(
        self, screenshot: Image | bytes, instruction: str | None = None
    ) -> Step:
        """Send screenshot to the server and get the next actions.

        Args:
            screenshot: Screenshot as Image object or raw bytes
            instruction: Optional additional instruction for this step (only works with existing task_id)

        Returns:
            Step: The actions and reasoning for this step
        """
        if not self.task_description:
            raise ValueError("Task description must be set. Call init_task() first.")

        logger.debug(f"Executing async step for task: '{self.task_description}'")

        try:
            # Convert Image to bytes using the protocol
            if isinstance(screenshot, Image):
                screenshot_bytes = screenshot.read()
            else:
                screenshot_bytes = screenshot
            screenshot_b64 = encode_screenshot_from_bytes(screenshot_bytes)

            # Call API
            response = await self.client.create_message(
                model=self.model,
                screenshot=screenshot_b64,
                task_description=self.task_description,
                task_id=self.task_id,
                instruction=instruction,
            )

            # Update task_id from response
            if self.task_id != response.task_id:
                if self.task_id is None:
                    logger.debug(f"Task ID assigned: {response.task_id}")
                else:
                    logger.debug(
                        f"Task ID changed: {self.task_id} -> {response.task_id}"
                    )
                self.task_id = response.task_id

            # Convert API response to Step
            result = Step(
                reason=response.reason,
                actions=response.actions,
                stop=response.is_complete,
            )

            if response.is_complete:
                logger.info(f"Async task completed after {response.current_step} steps")
            else:
                logger.debug(
                    f"Async step {response.current_step} completed with {len(response.actions)} actions"
                )

            return result

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
