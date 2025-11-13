# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import io

from ..exceptions import check_optional_dependency
from ..types.models.image_config import ImageConfig

check_optional_dependency("PIL", "PILImage", "desktop")
from PIL import Image as PILImageLib  # noqa: E402


class PILImage:
    """PIL image wrapper with transformation capabilities."""

    def __init__(self, image: PILImageLib.Image, config: ImageConfig | None = None):
        """Initialize with a PIL image and optional config."""
        self.image = image
        self.config = config or ImageConfig()
        self._cached_bytes: bytes | None = None

    @classmethod
    def from_file(cls, path: str, config: ImageConfig | None = None) -> "PILImage":
        """Create PILImage from file path."""
        image = PILImageLib.open(path)
        return cls(image, config)

    @classmethod
    def from_bytes(cls, data: bytes, config: ImageConfig | None = None) -> "PILImage":
        """Create PILImage from raw bytes."""
        image = PILImageLib.open(io.BytesIO(data))
        return cls(image, config)

    @classmethod
    def from_screenshot(cls, config: ImageConfig | None = None) -> "PILImage":
        """Create PILImage from screenshot."""
        # Lazy import to avoid DISPLAY issues in headless environments
        check_optional_dependency("pyautogui", "PILImage.from_screenshot()", "desktop")
        import pyautogui  # noqa: PLC0415

        screenshot = pyautogui.screenshot()
        return cls(screenshot, config)

    def transform(self, config: ImageConfig) -> "PILImage":
        """Apply transformations (resize) based on config and return new PILImage."""
        # Apply resize if needed
        transformed = self._resize(self.image, config)
        # Return new PILImage with the config (format conversion happens on read())
        return PILImage(transformed, config)

    def _resize(
        self, image: PILImageLib.Image, config: ImageConfig
    ) -> PILImageLib.Image:
        """Resize image based on config."""
        if config.width or config.height:
            # Get target dimensions (use original if not specified)
            target_width = config.width or image.width
            target_height = config.height or image.height

            # Map resample string to PIL constant
            resample_map = {
                "NEAREST": PILImageLib.NEAREST,
                "BILINEAR": PILImageLib.BILINEAR,
                "BICUBIC": PILImageLib.BICUBIC,
                "LANCZOS": PILImageLib.LANCZOS,
            }
            resample = resample_map[config.resample]

            # Resize to exact dimensions
            return image.resize((target_width, target_height), resample)
        return image

    def _convert_format(self, image: PILImageLib.Image) -> bytes:
        """Convert image to configured format (PNG or JPEG)."""
        buffer = io.BytesIO()
        save_kwargs = {"format": self.config.format}

        if self.config.format == "JPEG":
            save_kwargs["quality"] = self.config.quality
            # Convert RGBA to RGB for JPEG if needed
            if image.mode == "RGBA":
                rgb_image = PILImageLib.new("RGB", image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3])
                rgb_image.save(buffer, **save_kwargs)
            else:
                image.save(buffer, **save_kwargs)
        elif self.config.format == "PNG":
            save_kwargs["optimize"] = self.config.optimize
            image.save(buffer, **save_kwargs)

        return buffer.getvalue()

    def read(self) -> bytes:
        """Read image as bytes with current config (implements Image protocol)."""
        if self._cached_bytes is None:
            self._cached_bytes = self._convert_format(self.image)
        return self._cached_bytes
