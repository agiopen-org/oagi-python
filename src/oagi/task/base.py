# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from uuid import uuid4

from ..constants import (
    DEFAULT_MAX_STEPS,
    MAX_STEPS_ACTOR,
    MAX_STEPS_THINKER,
    MODEL_THINKER,
)
from ..logging import get_logger
from ..types import URL, Image, Step
from ..utils.prompt_builder import build_prompt

logger = get_logger("task.base")


class BaseActor:
    """Base class with shared task management logic for sync/async actors."""

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
        self.max_steps: int = DEFAULT_MAX_STEPS
        self.current_step: int = 0  # Current step counter
        # Client will be set by subclasses
        self.api_key: str | None = None
        self.base_url: str | None = None

    def _validate_max_steps(self, max_steps: int) -> int:
        """Validate and cap max_steps based on model type.

        Args:
            max_steps: Requested maximum number of steps

        Returns:
            Validated max_steps (capped to model limit if exceeded)
        """
        limit = MAX_STEPS_THINKER if self.model == MODEL_THINKER else MAX_STEPS_ACTOR
        if max_steps > limit:
            logger.warning(
                f"max_steps ({max_steps}) exceeds limit for model '{self.model}'. "
                f"Capping to {limit}."
            )
            return limit
        return max_steps

    def _prepare_init_task(
        self,
        task_desc: str,
        max_steps: int,
    ):
        """Prepare task initialization.

        Args:
            task_desc: Task description
            max_steps: Maximum number of steps
        """
        self.task_id = uuid4().hex
        self.task_description = task_desc
        self.message_history = []
        self.max_steps = self._validate_max_steps(max_steps)
        self.current_step = 0
        logger.info(f"Task initialized: '{task_desc}' (max_steps: {self.max_steps})")

    def _validate_and_increment_step(self):
        if not self.task_description:
            raise ValueError("Task description must be set. Call init_task() first.")
        if self.current_step >= self.max_steps:
            raise ValueError(
                f"Max steps limit ({self.max_steps}) reached. "
                "Call init_task() to start a new task."
            )
        self.current_step += 1

    def _get_temperature(self, temperature: float | None) -> float | None:
        return temperature if temperature is not None else self.temperature

    def _prepare_screenshot(self, screenshot: Image | bytes) -> bytes:
        if isinstance(screenshot, Image):
            return screenshot.read()
        return screenshot

    def _get_screenshot_url(self, screenshot: Image | URL | bytes) -> str | None:
        """Get screenshot URL if it's a string, otherwise return None."""
        if isinstance(screenshot, str):
            return screenshot
        return None

    def _ensure_screenshot_url_sync(
        self, screenshot: Image | URL | bytes, client
    ) -> str:
        """Get screenshot URL, uploading to S3 if needed (sync version).

        Args:
            screenshot: Screenshot as Image object, URL string, or raw bytes
            client: SyncClient instance for S3 upload

        Returns:
            Screenshot URL (either direct or from S3 upload)
        """
        screenshot_url = self._get_screenshot_url(screenshot)
        if screenshot_url is None:
            screenshot_bytes = self._prepare_screenshot(screenshot)
            upload_response = client.put_s3_presigned_url(screenshot_bytes)
            screenshot_url = upload_response.download_url
        return screenshot_url

    async def _ensure_screenshot_url_async(
        self, screenshot: Image | URL | bytes, client
    ) -> str:
        """Get screenshot URL, uploading to S3 if needed (async version).

        Args:
            screenshot: Screenshot as Image object, URL string, or raw bytes
            client: AsyncClient instance for S3 upload

        Returns:
            Screenshot URL (either direct or from S3 upload)
        """
        screenshot_url = self._get_screenshot_url(screenshot)
        if screenshot_url is None:
            screenshot_bytes = self._prepare_screenshot(screenshot)
            upload_response = await client.put_s3_presigned_url(screenshot_bytes)
            screenshot_url = upload_response.download_url
        return screenshot_url

    def _add_user_message_to_history(
        self, screenshot_url: str, prompt: str | None = None
    ):
        """Add user message with screenshot to message history.

        Args:
            screenshot_url: URL of the screenshot
            prompt: Optional prompt text (for first message only)
        """
        content = []
        if prompt:
            content.append({"type": "text", "text": prompt})
        content.append({"type": "image_url", "image_url": {"url": screenshot_url}})

        self.message_history.append(
            {
                "role": "user",
                "content": content,
            }
        )

    def _add_assistant_message_to_history(self, raw_output: str):
        """Add assistant response to message history.

        Args:
            raw_output: Raw model output string
        """
        if raw_output:
            self.message_history.append(
                {
                    "role": "assistant",
                    "content": raw_output,
                }
            )

    def _build_step_prompt(self) -> str | None:
        """Build prompt for first message only."""
        if len(self.message_history) == 0:
            return build_prompt(self.task_description)
        return None

    def _log_step_completion(self, step: Step, prefix: str = "") -> None:
        """Log step completion status."""
        if step.stop:
            logger.info(f"{prefix}Task completed.")
        else:
            logger.debug(f"{prefix}Step completed with {len(step.actions)} actions")

    def _log_step_execution(self, prefix: str = ""):
        logger.debug(f"Executing {prefix}step for task: '{self.task_description}'")

    def _handle_step_error(self, error: Exception, prefix: str = ""):
        logger.error(f"Error during {prefix}step execution: {error}")
        raise


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
