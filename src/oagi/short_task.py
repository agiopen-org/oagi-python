# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Optional

from .sync_client import SyncClient, encode_screenshot_from_bytes
from .types import ActionHandler, Image, ImageProvider, Step


class ShortTask:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.client = SyncClient(base_url=base_url, api_key=api_key)
        self.api_key = self.client.api_key
        self.base_url = self.client.base_url
        self.task_id: Optional[str] = None
        self.task_description: Optional[str] = None
        self.model = "vision-model-v1"  # default model

    def init_task(self, task_desc: str, max_steps: int = 5):
        """Initialize a new task with the given description."""
        self.task_description = task_desc
        self.task_id = None  # Reset task_id for new task

    def step(self, screenshot: Image) -> Step:
        """Send screenshot to the server and get the next actions."""
        if not self.task_description:
            raise ValueError("Task description must be set. Call init_task() first.")

        # Convert Image to base64 string
        # Assuming Image is bytes-like or has a method to get bytes
        if hasattr(screenshot, "read"):
            # If it's file-like
            screenshot_bytes = screenshot.read()
        elif isinstance(screenshot, bytes):
            screenshot_bytes = screenshot
        else:
            # If it's a path string or other format, handle accordingly
            raise ValueError(
                "Unsupported screenshot format. Expected bytes or file-like object."
            )

        screenshot_b64 = encode_screenshot_from_bytes(screenshot_bytes)

        # Call API
        response = self.client.create_message(
            model=self.model,
            screenshot=screenshot_b64,
            task_description=self.task_description if self.task_id is None else None,
            task_id=self.task_id,
        )

        # Update task_id from response
        self.task_id = response.task_id

        # Convert API response to Step
        result = Step(
            reason=f"Step {response.current_step}: Analyzing task '{response.task_description}'",
            actions=response.actions,
            stop=response.is_complete,
        )
        return result

    def close(self):
        """Close the underlying HTTP client to free resources."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def auto_mode(
        self,
        task_desc: str,
        max_steps: int = 5,
        executor: ActionHandler = None,
        image_provider: ImageProvider = None,
    ) -> bool:
        """Run the task in automatic mode with the provided executor and image provider."""
        self.init_task(task_desc, max_steps=max_steps)

        for i in range(max_steps):
            image = image_provider()
            step = self.step(image)
            if step.stop:
                return True
            if executor:
                executor(step.actions)

        return False
