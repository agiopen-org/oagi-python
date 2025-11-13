# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import asyncio

from ..types import Image, ImageConfig
from .screenshot_maker import ScreenshotMaker


class AsyncScreenshotMaker:
    """
    Async wrapper for ScreenshotMaker that captures screenshots in a thread pool.

    This allows screenshot capture to be non-blocking in async contexts,
    enabling concurrent execution of other async tasks while screenshots are taken.
    """

    def __init__(self, config: ImageConfig | None = None):
        """Initialize with optional image configuration.

        Args:
            config: ImageConfig instance for customizing screenshot format and quality
        """
        self.sync_screenshot_maker = ScreenshotMaker(config=config)
        self.config = config

    async def __call__(self) -> Image:
        """
        Capture a screenshot asynchronously using a thread pool executor.

        This prevents screenshot capture from blocking the async event loop,
        allowing other coroutines to run while the screenshot is being taken.

        Returns:
            Image: The captured screenshot as a PILImage
        """
        loop = asyncio.get_event_loop()
        # Run the synchronous screenshot capture in a thread pool to avoid blocking
        return await loop.run_in_executor(None, self.sync_screenshot_maker)

    async def last_image(self) -> Image:
        return self.sync_screenshot_maker.last_image()
