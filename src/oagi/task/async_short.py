# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import warnings

from ..logging import get_logger
from ..types import AsyncActionHandler, AsyncImageProvider
from .async_ import AsyncActor
from .base import BaseAutoMode

logger = get_logger("async_short_task")


class AsyncShortTask(AsyncActor, BaseAutoMode):
    """Deprecated: This class is deprecated and will be removed in a future version.

    Async task implementation with automatic mode for short-duration tasks.
    Please use AsyncActor directly with custom automation logic instead.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-actor-1",
        temperature: float | None = None,
    ):
        warnings.warn(
            "AsyncShortTask is deprecated and will be removed in a future version. "
            "Please use AsyncActor with custom automation logic instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            api_key=api_key, base_url=base_url, model=model, temperature=temperature
        )

    async def auto_mode(
        self,
        task_desc: str,
        max_steps: int = 5,
        executor: AsyncActionHandler = None,
        image_provider: AsyncImageProvider = None,
        temperature: float | None = None,
    ) -> bool:
        """Run the task in automatic mode with the provided executor and image provider.

        Args:
            task_desc: Task description
            max_steps: Maximum number of steps
            executor: Async handler to execute actions
            image_provider: Async provider for screenshots
            temperature: Sampling temperature for all steps (overrides task default if provided)
        """
        self._log_auto_mode_start(task_desc, max_steps, prefix="async ")

        await self.init_task(task_desc, max_steps=max_steps)

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
