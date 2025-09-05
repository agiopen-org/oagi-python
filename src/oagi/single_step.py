# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from pathlib import Path

from .pil_image import PILImage
from .task import Task
from .types import Image, Step


def single_step(
    task_description: str,
    screenshot: str | bytes | Path | Image,
    instruction: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> Step:
    """
    Perform a single-step inference without maintaining task state.

    This is useful for one-off analyses where you don't need to maintain
    a conversation or task context across multiple steps.

    Args:
        task_description: Description of the task to perform
        screenshot: Screenshot as Image, bytes, or file path
        instruction: Optional additional instruction for the task
        api_key: OAGI API key (uses environment variable if not provided)
        base_url: OAGI base URL (uses environment variable if not provided)

    Returns:
        Step: Object containing reasoning, actions, and completion status

    Example:
        >>> # Using with bytes
        >>> with open("screenshot.png", "rb") as f:
        ...     image_bytes = f.read()
        >>> step = single_step(
        ...     task_description="Click the submit button",
        ...     screenshot=image_bytes
        ... )

        >>> # Using with file path
        >>> step = single_step(
        ...     task_description="Fill in the form",
        ...     screenshot=Path("screenshot.png"),
        ...     instruction="Use test@example.com for email"
        ... )

        >>> # Using with Image object
        >>> from oagi.types import Image
        >>> image = Image(...)
        >>> step = single_step(
        ...     task_description="Navigate to settings",
        ...     screenshot=image
        ... )
    """
    # Convert file paths to bytes using PILImage
    if isinstance(screenshot, (str, Path)):
        path = Path(screenshot) if isinstance(screenshot, str) else screenshot
        if path.exists():
            pil_image = PILImage.from_file(str(path))
            screenshot_bytes = pil_image.read()
        else:
            raise FileNotFoundError(f"Screenshot file not found: {path}")
    elif isinstance(screenshot, bytes):
        screenshot_bytes = screenshot
    elif isinstance(screenshot, Image):
        screenshot_bytes = screenshot.read()
    else:
        raise ValueError(
            f"screenshot must be Image, bytes, str, or Path, got {type(screenshot)}"
        )

    # Use Task to perform single step
    with Task(api_key=api_key, base_url=base_url) as task:
        task.init_task(task_description)
        return task.step(screenshot_bytes, instruction=instruction)
