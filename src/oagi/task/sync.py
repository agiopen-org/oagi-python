# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import warnings

from ..client import SyncClient
from ..types import URL, Image, Step
from .base import BaseActor


class Actor(BaseActor):
    """Base class for task automation with the OAGI API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-actor-1",
        temperature: float | None = None,
    ):
        super().__init__(api_key, base_url, model, temperature)
        self.client = SyncClient(base_url=base_url, api_key=api_key)
        self.api_key = self.client.api_key
        self.base_url = self.client.base_url

    def init_task(
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

    def step(
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
        kwargs = self._prepare_step(screenshot, instruction, temperature)

        try:
            response = self.client.create_message(**kwargs)
            return self._build_step_response(response)
        except Exception as e:
            self._handle_step_error(e)

    def close(self):
        """Close the underlying HTTP client to free resources."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class Task(Actor):
    """Deprecated: Use Actor instead.

    This class is deprecated and will be removed in a future version.
    Please use Actor instead.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-actor-1",
        temperature: float | None = None,
    ):
        warnings.warn(
            "Task is deprecated and will be removed in a future version. "
            "Please use Actor instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(api_key, base_url, model, temperature)
