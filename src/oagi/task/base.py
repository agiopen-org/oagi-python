# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import base64

from ..logging import get_logger
from ..types import Image, Step
from ..types.models import LLMResponse

logger = get_logger("task.base")


def encode_screenshot_from_bytes(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def encode_screenshot_from_file(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return encode_screenshot_from_bytes(f.read())


class BaseTask:
    """Base class with shared task management logic for sync/async tasks."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None,
        model: str,
        temperature: float | None,
    ):
        self.task_id: str | None = None
        self.task_description: str | None = None
        self.model = model
        self.temperature = temperature
        self.last_task_id: str | None = None
        self.history_steps: int | None = None
        # Client will be set by subclasses
        self.api_key: str | None = None
        self.base_url: str | None = None

    def _prepare_init_task(
        self,
        task_desc: str,
        last_task_id: str | None = None,
        history_steps: int | None = None,
    ):
        self.task_description = task_desc
        self.last_task_id = last_task_id
        self.history_steps = history_steps

    def _process_init_response(
        self, response: LLMResponse, task_desc: str, max_steps: int, prefix: str = ""
    ):
        self.task_id = response.task_id  # Reset task_id for new task
        logger.info(f"{prefix}Task initialized: '{task_desc}' (max_steps: {max_steps})")
        if self.last_task_id:
            logger.info(
                f"Will include {self.history_steps or 1} steps from previous task: {self.last_task_id}"
            )

    def _validate_step_preconditions(self):
        if not self.task_description:
            raise ValueError("Task description must be set. Call init_task() first.")

    def _prepare_screenshot(self, screenshot: Image | bytes) -> bytes:
        if isinstance(screenshot, Image):
            return screenshot.read()
        return screenshot

    def _get_temperature(self, temperature: float | None) -> float | None:
        return temperature if temperature is not None else self.temperature

    def _update_task_id(self, response: LLMResponse):
        if self.task_id != response.task_id:
            if self.task_id is None:
                logger.debug(f"Task ID assigned: {response.task_id}")
            else:
                logger.debug(f"Task ID changed: {self.task_id} -> {response.task_id}")
            self.task_id = response.task_id

    def _build_step_response(self, response: LLMResponse, prefix: str = "") -> Step:
        result = Step(
            reason=response.reason,
            actions=response.actions,
            stop=response.is_complete,
        )

        if response.is_complete:
            logger.info(f"{prefix}Task completed after {response.current_step} steps")
        else:
            logger.debug(
                f"{prefix}Step {response.current_step} completed with {len(response.actions)} actions"
            )

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
