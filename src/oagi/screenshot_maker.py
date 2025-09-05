# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import io
from typing import Optional

import pyautogui
from PIL import Image as PILImage

from .types import Image
from .types.models.image_config import ImageConfig


class FileImage:
    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()

    def read(self) -> bytes:
        return self.data


class MockImage:
    def read(self) -> bytes:
        return b"mock screenshot data"


class ScreenshotImage:
    """Image class that wraps a pyautogui screenshot."""

    def __init__(self, screenshot, config: ImageConfig | None = None):
        """Initialize with a PIL Image from pyautogui."""
        self.screenshot = screenshot
        self.config = config or ImageConfig()
        self._cached_bytes: Optional[bytes] = None

    def _convert_format(self, image: PILImage.Image) -> bytes:
        """Convert image to configured format (PNG or JPEG)."""
        buffer = io.BytesIO()
        save_kwargs = {"format": self.config.format}

        if self.config.format == "JPEG":
            save_kwargs["quality"] = self.config.quality
            # Convert RGBA to RGB for JPEG if needed
            if image.mode == "RGBA":
                rgb_image = PILImage.new("RGB", image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3])
                rgb_image.save(buffer, **save_kwargs)
            else:
                image.save(buffer, **save_kwargs)
        elif self.config.format == "PNG":
            save_kwargs["optimize"] = self.config.optimize
            image.save(buffer, **save_kwargs)

        return buffer.getvalue()

    def read(self) -> bytes:
        """Convert the screenshot to bytes with configured format."""
        if self._cached_bytes is None:
            # Convert format (this happens after any resizing)
            self._cached_bytes = self._convert_format(self.screenshot)
        return self._cached_bytes


class ScreenshotMaker:
    """Takes screenshots using pyautogui."""

    def __init__(self, config: ImageConfig | None = None):
        self.config = config or ImageConfig()
        self._last_screenshot: Optional[ScreenshotImage] = None

    def _resize_image(self, image: PILImage.Image) -> PILImage.Image:
        """Resize image to configured dimensions if specified."""
        if self.config.width or self.config.height:
            # Get target dimensions (use original if not specified)
            target_width = self.config.width or image.width
            target_height = self.config.height or image.height

            # Map resample string to PIL constant
            resample_map = {
                "NEAREST": PILImage.NEAREST,
                "BILINEAR": PILImage.BILINEAR,
                "BICUBIC": PILImage.BICUBIC,
                "LANCZOS": PILImage.LANCZOS,
            }
            resample = resample_map[self.config.resample]

            # Resize to exact dimensions
            return image.resize((target_width, target_height), resample)
        return image

    def __call__(self) -> Image:
        """Take a screenshot and return it as an Image."""
        # Step 1: Take a screenshot using pyautogui
        screenshot = pyautogui.screenshot()

        # Step 2: Resize the image (if configured)
        resized_screenshot = self._resize_image(screenshot)

        # Step 3: Wrap in ScreenshotImage (format conversion happens on read())
        screenshot_image = ScreenshotImage(resized_screenshot, self.config)

        # Store as the last screenshot
        self._last_screenshot = screenshot_image

        return screenshot_image

    def last_image(self) -> Image:
        """Return the last screenshot taken, or take a new one if none exists."""
        if self._last_screenshot is None:
            return self()
        return self._last_screenshot
