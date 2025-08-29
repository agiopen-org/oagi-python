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

from .types import Image


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

    def __init__(self, screenshot):
        """Initialize with a PIL Image from pyautogui."""
        self.screenshot = screenshot
        self._cached_bytes: Optional[bytes] = None

    def read(self) -> bytes:
        """Convert the screenshot to bytes (PNG format)."""
        if self._cached_bytes is None:
            # Convert PIL Image to bytes
            buffer = io.BytesIO()
            self.screenshot.save(buffer, format="PNG")
            self._cached_bytes = buffer.getvalue()
        return self._cached_bytes


class ScreenshotMaker:
    """Takes screenshots using pyautogui."""

    def __init__(self):
        self._last_screenshot: Optional[ScreenshotImage] = None

    def __call__(self) -> Image:
        """Take a screenshot and return it as an Image."""
        # Take a screenshot using pyautogui
        screenshot = pyautogui.screenshot()

        # Wrap it in our ScreenshotImage class
        screenshot_image = ScreenshotImage(screenshot)

        # Store as the last screenshot
        self._last_screenshot = screenshot_image

        return screenshot_image

    def last_image(self) -> Image:
        """Return the last screenshot taken, or take a new one if none exists."""
        if self._last_screenshot is None:
            return self()
        return self._last_screenshot
