# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from .logging import get_logger
from .task import Task
from .types import ActionHandler, ImageProvider

logger = get_logger("short_task")


class ShortTask(Task):
    """Task implementation with automatic mode for short-duration tasks."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "vision-model-v1",
    ):
        super().__init__(api_key=api_key, base_url=base_url, model=model)

    def auto_mode(
        self,
        task_desc: str,
        max_steps: int = 5,
        executor: ActionHandler = None,
        image_provider: ImageProvider = None,
    ) -> bool:
        """Run the task in automatic mode with the provided executor and image provider."""
        logger.info(
            f"Starting auto mode for task: '{task_desc}' (max_steps: {max_steps})"
        )
        self.init_task(task_desc, max_steps=max_steps)

        for i in range(max_steps):
            logger.debug(f"Auto mode step {i + 1}/{max_steps}")
            image = image_provider()
            step = self.step(image)
            if executor:
                logger.debug(f"Executing {len(step.actions)} actions")
                executor(step.actions)
            if step.stop:
                logger.info(f"Auto mode completed successfully after {i + 1} steps")
                return True

        logger.warning(f"Auto mode reached max steps ({max_steps}) without completion")
        return False
