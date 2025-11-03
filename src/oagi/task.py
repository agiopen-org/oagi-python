# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from uuid import uuid4

from .logging import get_logger
from .sync_client import SyncClient
from .types import Image, Step

logger = get_logger("task")


class Task:
    """Base class for task automation with the OAGI API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "vision-model-v1",
    ):
        self.client = SyncClient(base_url=base_url, api_key=api_key)
        self.api_key = self.client.api_key
        self.base_url = self.client.base_url
        self.task_id = uuid4().hex
        self.task_description: str | None = None
        self.model = model
        self.message_history: list = []
        self.last_task_id: str | None = None
        self.history_steps: int | None = None

    def init_task(
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
        self.task_description = task_desc
        self.max_steps = max_steps
        logger.info(f"Task initialized: '{task_desc}' (max_steps: {max_steps})")

    def step(self, screenshot: Image | bytes, instruction: str | None = None) -> Step:
        """Send screenshot to the server and get the next actions.

        Args:
            screenshot: Screenshot as Image object or raw bytes
            instruction: Optional additional instruction for this step (only works with existing task_id)

        Returns:
            Step: The actions and reasoning for this step
        """
        if not self.task_description:
            raise ValueError("Task description must be set. Call init_task() first.")

        logger.debug(f"Executing step for task: '{self.task_description}'")

        try:
            # Convert Image to bytes using the protocol
            if isinstance(screenshot, Image):
                screenshot_bytes = screenshot.read()
            else:
                screenshot_bytes = screenshot

            # Call API
            response = self.client.create_message(
                model=self.model,
                screenshot=screenshot_bytes,
                task_description=self.task_description,
                task_id=self.task_id,
                instruction=instruction,
                messages_history=self.message_history,
            )

            # Append instruction message if provided
            if response.raw_output:
                self.message_history.append(
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": response.raw_output}],
                    }
                )

            # Convert API response to Step
            result = Step(
                reason=response.reason,
                actions=response.actions,
                stop=response.is_complete,
            )

            if response.is_complete:
                logger.info("Task completed.")
            else:
                logger.debug(f"Step completed with {len(response.actions)} actions")

            return result

        except Exception as e:
            logger.error(f"Error during step execution: {e}")
            raise

    def close(self):
        """Close the underlying HTTP client to free resources."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
