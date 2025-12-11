# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import asyncio
import logging

from .. import AsyncActor
from ..constants import (
    DEFAULT_MAX_STEPS,
    DEFAULT_STEP_DELAY,
    DEFAULT_TEMPERATURE,
    MODEL_ACTOR,
)
from ..handler import reset_handler
from ..types import (
    ActionEvent,
    AsyncActionHandler,
    AsyncImageProvider,
    AsyncObserver,
    Image,
    StepEvent,
)

logger = logging.getLogger(__name__)


def _serialize_image(image: Image | str) -> bytes | str:
    """Convert an image to bytes or keep URL as string."""
    if isinstance(image, str):
        return image
    return image.read()


class AsyncDefaultAgent:
    """Default asynchronous agent implementation using OAGI client."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = MODEL_ACTOR,
        max_steps: int = DEFAULT_MAX_STEPS,
        temperature: float | None = DEFAULT_TEMPERATURE,
        step_observer: AsyncObserver | None = None,
        step_delay: float = DEFAULT_STEP_DELAY,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_steps = max_steps
        self.temperature = temperature
        self.step_observer = step_observer
        self.step_delay = step_delay

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

            # Reset handler state at automation start
            reset_handler(action_handler)

            for i in range(self.max_steps):
                step_num = i + 1
                logger.debug(f"Executing step {step_num}/{self.max_steps}")

                # Capture current state
                image = await image_provider()

                # Get next step from OAGI
                step = await self.actor.step(image, temperature=self.temperature)

                # Log reasoning
                if step.reason:
                    logger.info(f"Step {step_num}: {step.reason}")

                # Emit step event
                if self.step_observer:
                    await self.step_observer.on_event(
                        StepEvent(
                            step_num=step_num,
                            image=_serialize_image(image),
                            step=step,
                            task_id=self.actor.task_id,
                        )
                    )

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

                    error = None
                    try:
                        await action_handler(step.actions)
                    except Exception as e:
                        error = str(e)
                        raise

                    # Emit action event
                    if self.step_observer:
                        await self.step_observer.on_event(
                            ActionEvent(
                                step_num=step_num,
                                actions=step.actions,
                                error=error,
                            )
                        )

                # Wait after actions before next screenshot
                if self.step_delay > 0:
                    await asyncio.sleep(self.step_delay)

                # Check if task is complete
                if step.stop:
                    logger.info(f"Task completed successfully after {step_num} steps")
                    return True

            logger.warning(
                f"Task reached max steps ({self.max_steps}) without completion"
            )
            return False
