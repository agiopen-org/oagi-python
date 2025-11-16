# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import logging

from .. import AsyncActor
from ..types import (
    AsyncActionHandler,
    AsyncImageProvider,
    AsyncStepObserver,
)

logger = logging.getLogger(__name__)


class AsyncDefaultAgent:
    """Default asynchronous agent implementation using OAGI client."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-actor-1",
        max_steps: int = 20,
        temperature: float | None = 0.5,
        step_observer: AsyncStepObserver | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_steps = max_steps
        self.temperature = temperature
        self.step_observer = step_observer

    async def execute(
        self,
        instruction: str,
        action_handler: AsyncActionHandler,
        image_provider: AsyncImageProvider,
    ) -> bool:
        async with AsyncActor(
            api_key=self.api_key, base_url=self.base_url, model=self.model
        ) as self.actor:
            logger.info(f"Starting async task execution: {instruction}")
            await self.actor.init_task(instruction, max_steps=self.max_steps)

            for i in range(self.max_steps):
                logger.debug(f"Executing step {i + 1}/{self.max_steps}")

                # Capture current state
                image = await image_provider()

                # Get next step from OAGI
                step = await self.actor.step(image, temperature=self.temperature)

                # Log reasoning
                if step.reason:
                    logger.info(f"Step {i + 1}: {step.reason}")

                # Notify observer if present
                if self.step_observer:
                    await self.step_observer.on_step(i + 1, step.reason, step.actions)

                # Execute actions if any
                if step.actions:
                    logger.info(f"Actions ({len(step.actions)}):")
                    for action in step.actions:
                        count_suffix = (
                            f" x{action.count}"
                            if action.count and action.count > 1
                            else ""
                        )
                        logger.info(
                            f"  [{action.type.value}] {action.argument}{count_suffix}"
                        )
                    await action_handler(step.actions)

                # Check if task is complete
                if step.stop:
                    logger.info(f"Task completed successfully after {i + 1} steps")
                    return True

            logger.warning(
                f"Task reached max steps ({self.max_steps}) without completion"
            )
            return False
