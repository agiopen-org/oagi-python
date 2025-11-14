# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from uuid import uuid4

from ..logging import get_logger
from ..types import Image, Step, URLImage
from ..types.models import LLMResponse

logger = get_logger("task.base")


class BaseTask:
    """Base class with shared task management logic for sync/async tasks."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None,
        model: str,
        temperature: float | None,
    ):
        self.task_id: str = uuid4().hex  # Client-side generated UUID
        self.task_description: str | None = None
        self.model = model
        self.temperature = temperature
        self.message_history: list = []  # OpenAI-compatible message history
        # Client will be set by subclasses
        self.api_key: str | None = None
        self.base_url: str | None = None

    def _prepare_init_task(
        self,
        task_desc: str,
        max_steps: int,
    ):
        """Prepare task initialization (v2 API does not call server for init).

        Args:
            task_desc: Task description
            max_steps: Maximum number of steps
        """
        self.task_id = uuid4().hex
        self.task_description = task_desc
        self.message_history = []
        logger.info(f"Task initialized: '{task_desc}' (max_steps: {max_steps})")

    def _validate_step_preconditions(self):
        if not self.task_description:
            raise ValueError("Task description must be set. Call init_task() first.")

    def _prepare_screenshot(self, screenshot: Image | bytes) -> bytes:
        if isinstance(screenshot, Image):
            return screenshot.read()
        return screenshot

    def _get_temperature(self, temperature: float | None) -> float | None:
        return temperature if temperature is not None else self.temperature

    def _prepare_screenshot_kwargs(self, screenshot: Image | bytes) -> dict:
        if isinstance(screenshot, URLImage):
            return {"screenshot_url": screenshot.get_url()}
        return {"screenshot": self._prepare_screenshot(screenshot)}

    def _handle_response_message_history(self, response: LLMResponse):
        if response.raw_output:
            self.message_history.append(
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": response.raw_output}],
                }
            )

    def _build_step_response(self, response: LLMResponse, prefix: str = "") -> Step:
        # Update message history with assistant response
        self._handle_response_message_history(response)

        result = Step(
            reason=response.reason,
            actions=response.actions,
            stop=response.is_complete,
        )

        if response.is_complete:
            logger.info(f"{prefix}Task completed.")
        else:
            logger.debug(f"{prefix}Step completed with {len(response.actions)} actions")

        return result

    def _log_step_execution(self, prefix: str = ""):
        logger.debug(f"Executing {prefix}step for task: '{self.task_description}'")


class BaseAutoMode:
    """Base class with shared auto_mode logic for ShortTask implementations."""

    def _log_auto_mode_start(self, task_desc: str, max_steps: int, prefix: str = ""):
        logger.info(
            f"Starting {prefix}auto mode for task: '{task_desc}' (max_steps: {max_steps})"
        )

    def _log_auto_mode_step(self, step_num: int, max_steps: int, prefix: str = ""):
        logger.debug(f"{prefix.capitalize()}auto mode step {step_num}/{max_steps}")

    def _log_auto_mode_actions(self, action_count: int, prefix: str = ""):
        verb = "asynchronously" if "async" in prefix else ""
        logger.debug(f"Executing {action_count} actions {verb}".strip())

    def _log_auto_mode_completion(self, steps: int, prefix: str = ""):
        logger.info(
            f"{prefix.capitalize()}auto mode completed successfully after {steps} steps"
        )

    def _log_auto_mode_max_steps(self, max_steps: int, prefix: str = ""):
        logger.warning(
            f"{prefix.capitalize()}auto mode reached max steps ({max_steps}) without completion"
        )
