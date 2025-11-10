"""Default agent implementations using OAGI client."""

import logging
from typing import Optional

from .. import AsyncTask
from ..types import (
    AsyncActionHandler,
    AsyncImageProvider,
)

logger = logging.getLogger(__name__)


class AsyncDefaultAgent:
    """Default asynchronous agent implementation using OAGI client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "lux-v1",
        max_steps: int = 30,
        temperature: Optional[float] = None,
    ):
        """Initialize the async default agent.

        Args:
            api_key: OAGI API key
            base_url: OAGI API base URL
            model: Model to use for LLM inference
            max_steps: Maximum number of steps to execute
            temperature: Optional temperature for LLM sampling
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_steps = max_steps
        self.temperature = temperature

    async def execute(
        self,
        instruction: str,
        action_handler: AsyncActionHandler,
        image_provider: AsyncImageProvider,
    ) -> bool:
        """Asynchronously execute a task with the given handlers.

        Args:
            instruction: Task instruction to execute
            action_handler: Handler for executing actions
            image_provider: Provider for capturing images

        Returns:
            True if task completed successfully, False otherwise
        """
        async with AsyncTask(
            api_key=self.api_key, base_url=self.base_url, model=self.model
        ) as self.task:
            logger.info(f"Starting async task execution: {instruction}")
            await self.task.init_task(instruction, max_steps=self.max_steps)

            for i in range(self.max_steps):
                logger.debug(f"Executing step {i + 1}/{self.max_steps}")

                # Capture current state
                image = await image_provider()
                print(image.get_url())

                # Get next step from OAGI
                step = await self.task.step(image, temperature=self.temperature)

                # Log reasoning
                if step.reason:
                    logger.debug(f"Step {i + 1} reasoning: {step.reason}")

                # Execute actions if any
                if step.actions:
                    logger.debug(f"Executing {len(step.actions)} actions")
                    await action_handler(step.actions)

                # Check if task is complete
                if step.stop:
                    logger.info(f"Task completed successfully after {i + 1} steps")
                    return True

            logger.warning(
                f"Task reached max steps ({self.max_steps}) without completion"
            )
            return False
