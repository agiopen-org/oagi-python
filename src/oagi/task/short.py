# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import warnings

from ..logging import get_logger
from ..types import ActionHandler, ImageProvider
from .base import BaseAutoMode
from .sync import Actor

logger = get_logger("short_task")


class ShortTask(Actor, BaseAutoMode):
    """Deprecated: This class is deprecated and will be removed in a future version.

    Task implementation with automatic mode for short-duration tasks.
    Please use Actor directly with custom automation logic instead.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-actor-1",
        temperature: float | None = None,
    ):
        warnings.warn(
            "ShortTask is deprecated and will be removed in a future version. "
            "Please use Actor with custom automation logic instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            api_key=api_key, base_url=base_url, model=model, temperature=temperature
        )

    def auto_mode(
        self,
        task_desc: str,
        max_steps: int = 5,
        executor: ActionHandler = None,
        image_provider: ImageProvider = None,
        temperature: float | None = None,
    ) -> bool:
        """Run the task in automatic mode with the provided executor and image provider.

        Args:
            task_desc: Task description
            max_steps: Maximum number of steps
            executor: Handler to execute actions
            image_provider: Provider for screenshots
            temperature: Sampling temperature for all steps (overrides task default if provided)
        """
        self._log_auto_mode_start(task_desc, max_steps)

        self.init_task(task_desc, max_steps=max_steps)

        for i in range(max_steps):
            self._log_auto_mode_step(i + 1, max_steps)
            image = image_provider()
            step = self.step(image, temperature=temperature)
            if executor:
                self._log_auto_mode_actions(len(step.actions))
                executor(step.actions)
            if step.stop:
                self._log_auto_mode_completion(i + 1)
                return True

        self._log_auto_mode_max_steps(max_steps)
        return False
