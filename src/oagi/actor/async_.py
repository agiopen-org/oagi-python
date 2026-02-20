# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import warnings

from ..client import AsyncClient
from ..constants import DEFAULT_MAX_STEPS, MODEL_ACTOR
from ..logging import get_logger
from ..types import URL, Image, Step
from .base import BaseActor

logger = get_logger("actor.async")


class AsyncActor(BaseActor):
    """Async base class for task automation with the OAGI API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = MODEL_ACTOR,
        temperature: float | None = None,
        parser_mode: str = "qwen3",
    ):
        super().__init__(
            api_key,
            base_url,
            model,
            temperature,
            parser_mode=parser_mode,
        )
        self.client = AsyncClient(base_url=base_url, api_key=api_key)
        self.api_key = self.client.api_key
        self.base_url = self.client.base_url

    async def init_task(
        self,
        task_desc: str,
        max_steps: int = DEFAULT_MAX_STEPS,
    ):
        """Initialize a new task with the given description.

        Args:
            task_desc: Task description
            max_steps: Maximum number of steps allowed
        """
        self._prepare_init_task(task_desc, max_steps)

    async def step(
        self,
        screenshot: Image | URL | bytes,
        instruction: str | None = None,
        temperature: float | None = None,
        parser_mode: str | None = None,
    ) -> Step:
        """Send screenshot to the server and get the next actions.

        Args:
            screenshot: Screenshot as Image object, URL string, or raw bytes
            instruction: Optional additional instruction for this step (currently unused)
            temperature: Sampling temperature for this step (overrides task default if provided)
            parser_mode: Output parser mode for this request (defaults to actor setting)

        Returns:
            Step: The actions and reasoning for this step
        """
        self._validate_and_increment_step()
        self._log_step_execution(prefix="async ")

        try:
            screenshot_url = await self._ensure_screenshot_url_async(
                screenshot, self.client
            )
            self._add_user_message_to_history(screenshot_url, self._build_step_prompt())

            step, raw_output, usage = await self.client.chat_completion(
                model=self.model,
                messages=self.message_history,
                temperature=self._get_temperature(temperature),
                task_id=self.task_id,
                parser_mode=parser_mode or self.parser_mode,
            )

            self._add_assistant_message_to_history(raw_output)
            self._log_step_completion(step, prefix="Async ")
            return step

        except Exception as e:
            self._handle_step_error(e, prefix="async ")

    async def close(self):
        """Close the underlying HTTP client to free resources."""
        await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class AsyncTask(AsyncActor):
    """Deprecated: Use AsyncActor instead.

    This class is deprecated and will be removed in a future version.
    Please use AsyncActor instead.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = MODEL_ACTOR,
        temperature: float | None = None,
        parser_mode: str = "qwen3",
    ):
        warnings.warn(
            "AsyncTask is deprecated and will be removed in a future version. "
            "Please use AsyncActor instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            parser_mode=parser_mode,
        )
