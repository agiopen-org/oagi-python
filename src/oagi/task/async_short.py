# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from ..logging import get_logger
from ..types import AsyncActionHandler, AsyncImageProvider
from .async_ import AsyncTask
from .base import BaseAutoMode

logger = get_logger("async_short_task")


class AsyncShortTask(AsyncTask, BaseAutoMode):
    """Async task implementation with automatic mode for short-duration tasks."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "vision-model-v1",
        temperature: float | None = None,
    ):
        super().__init__(
            api_key=api_key, base_url=base_url, model=model, temperature=temperature
        )

    async def auto_mode(
        self,
        task_desc: str,
        max_steps: int = 5,
        executor: AsyncActionHandler = None,
        image_provider: AsyncImageProvider = None,
        last_task_id: str | None = None,
        history_steps: int | None = None,
        temperature: float | None = None,
    ) -> bool:
        """Run the task in automatic mode with the provided executor and image provider.

        Args:
            task_desc: Task description
            max_steps: Maximum number of steps
            executor: Async handler to execute actions
            image_provider: Async provider for screenshots
            last_task_id: Previous task ID to retrieve history from
            history_steps: Number of historical steps to include
            temperature: Sampling temperature for all steps (overrides task default if provided)
        """
        self._log_auto_mode_start(task_desc, max_steps, prefix="async ")

        await self.init_task(
            task_desc,
            max_steps=max_steps,
            last_task_id=last_task_id,
            history_steps=history_steps,
        )

        for i in range(max_steps):
            self._log_auto_mode_step(i + 1, max_steps, prefix="async ")
            image = await image_provider()
            step = await self.step(image, temperature=temperature)
            if executor:
                self._log_auto_mode_actions(len(step.actions), prefix="async ")
                await executor(step.actions)
            if step.stop:
                self._log_auto_mode_completion(i + 1, prefix="async ")
                return True

        self._log_auto_mode_max_steps(max_steps, prefix="async ")
        return False
