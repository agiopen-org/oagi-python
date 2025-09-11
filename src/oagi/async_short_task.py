# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from .async_task import AsyncTask
from .logging import get_logger
from .types import AsyncActionHandler, AsyncImageProvider

logger = get_logger("async_short_task")


class AsyncShortTask(AsyncTask):
    """Async task implementation with automatic mode for short-duration tasks."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "vision-model-v1",
    ):
        super().__init__(api_key=api_key, base_url=base_url, model=model)

    async def auto_mode(
        self,
        task_desc: str,
        max_steps: int = 5,
        executor: AsyncActionHandler = None,
        image_provider: AsyncImageProvider = None,
    ) -> bool:
        """Run the task in automatic mode with the provided executor and image provider."""
        logger.info(
            f"Starting async auto mode for task: '{task_desc}' (max_steps: {max_steps})"
        )
        await self.init_task(task_desc, max_steps=max_steps)

        for i in range(max_steps):
            logger.debug(f"Async auto mode step {i + 1}/{max_steps}")
            image = await image_provider()
            step = await self.step(image)
            if executor:
                logger.debug(f"Executing {len(step.actions)} actions asynchronously")
                await executor(step.actions)
            if step.stop:
                logger.info(
                    f"Async auto mode completed successfully after {i + 1} steps"
                )
                return True

        logger.warning(
            f"Async auto mode reached max steps ({max_steps}) without completion"
        )
        return False
