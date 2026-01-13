# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Optional

from oagi.handler.screen_manager import Screen

from ..types import Image
from ..types.models.image_config import ImageConfig
from .pil_image import PILImage


class ScreenshotMaker:
    """Takes screenshots using pyautogui."""

    def __init__(self, config: ImageConfig | None = None):
        self.config = config or ImageConfig()
        self._last_image: Optional[PILImage] = None
        self.region: Optional[tuple[int, int, int, int]] = None

    def set_target_screen(self, screen: Screen):
        """Set the target screen for screenshotting."""
        self.region = (screen.x, screen.y, screen.width, screen.height)

    def __call__(self) -> Image:
        """Take and process a screenshot."""
        # Create PILImage from screenshot
        pil_image = PILImage.from_screenshot(region=self.region)

        # Apply transformation if config is set
        if self.config:
            pil_image = pil_image.transform(self.config)

        # Store as the last image
        self._last_image = pil_image

        return pil_image

    def last_image(self) -> Image:
        """Return the last screenshot taken, or take a new one if none exists."""
        if self._last_image is None:
            return self()
        return self._last_image
