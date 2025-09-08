# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from pathlib import Path

from .async_task import AsyncTask
from .pil_image import PILImage
from .types import Image, Step


async def async_single_step(
    task_description: str,
    screenshot: str | bytes | Path | Image,
    instruction: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> Step:
    """
    Perform a single-step inference asynchronously without maintaining task state.

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
        >>> import asyncio
        >>> async def main():
        ...     with open("screenshot.png", "rb") as f:
        ...         screenshot_bytes = f.read()
        ...     step = await async_single_step(
        ...         "Click the submit button",
        ...         screenshot=screenshot_bytes
        ...     )
        ...     print(f"Actions: {step.actions}")
        >>> asyncio.run(main())

        >>> # Using with file path
        >>> step = await async_single_step(
        ...     "Find the search box",
        ...     screenshot="screenshot.png"
        ... )

        >>> # Using with PILImage
        >>> image = PILImage.from_file("screenshot.png")
        >>> step = await async_single_step(
        ...     "Click next page",
        ...     screenshot=image
        ... )
    """
    # Handle different screenshot input types
    if isinstance(screenshot, (str, Path)):
        # Convert file path to PILImage
        screenshot = PILImage.from_file(str(screenshot))
    elif isinstance(screenshot, bytes):
        # Convert bytes to PILImage
        screenshot = PILImage.from_bytes(screenshot)

    # Create a temporary task instance
    task = AsyncTask(api_key=api_key, base_url=base_url)

    try:
        # Initialize task and perform single step
        await task.init_task(task_description)
        result = await task.step(screenshot, instruction=instruction)
        return result
    finally:
        # Clean up resources
        await task.close()
