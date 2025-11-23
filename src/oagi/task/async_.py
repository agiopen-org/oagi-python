# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import warnings

from ..client import AsyncClient
from ..types import URL, Image, Step
from .base import BaseActor


class AsyncActor(BaseActor):
    """Async base class for task automation with the OAGI API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-actor-1",
        temperature: float | None = None,
    ):
        super().__init__(api_key, base_url, model, temperature)
        self.client = AsyncClient(base_url=base_url, api_key=api_key)
        self.api_key = self.client.api_key
        self.base_url = self.client.base_url

    async def init_task(
        self,
        task_desc: str,
        max_steps: int = 20,
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
    ) -> Step:
        """Send screenshot to the server and get the next actions.

        Args:
            screenshot: Screenshot as Image object or raw bytes
            instruction: Optional additional instruction for this step
            temperature: Sampling temperature for this step (overrides task default if provided)

        Returns:
            Step: The actions and reasoning for this step
        """
        kwargs = self._prepare_step(
            screenshot, instruction, temperature, prefix="async "
        )

        try:
            response = await self.client.create_message(**kwargs)
            return self._build_step_response(response, prefix="Async ")
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
        model: str = "lux-actor-1",
        temperature: float | None = None,
    ):
        warnings.warn(
            "AsyncTask is deprecated and will be removed in a future version. "
            "Please use AsyncActor instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(api_key, base_url, model, temperature)
