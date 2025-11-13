# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from oagi import ImageConfig, PILImage, ScreenshotMaker


def example_full_png_screenshot():
    """Example 1: Full-quality PNG screenshot without resizing."""
    print("Example 1: Full PNG screenshot without resizing")

    png_config = ImageConfig(
        format="PNG",
        width=None,  # No resizing - keep original width
        height=None,  # No resizing - keep original height
        optimize=True,  # Optimize PNG file size
    )

    screenshot_maker = ScreenshotMaker(config=png_config)
    full_png_screenshot = screenshot_maker()

    print(f"PNG screenshot dimensions: {full_png_screenshot.image.size}")
    print(f"PNG screenshot size: {len(full_png_screenshot.read())} bytes")
    return full_png_screenshot


def example_load_and_compress(file_name):
    """Example 2: Load image from file and convert to compressed JPEG."""
    print("\nExample 2: Load image from file and convert to JPEG")

    # Load an existing screenshot
    original_image = PILImage.from_file(file_name)
    print(f"Original image dimensions: {original_image.image.size}")

    # Create a config for compression
    jpeg_config = ImageConfig(
        format="JPEG",
        quality=70,  # Lower quality for smaller size
        width=1260,  # Resize to 1260px width
        height=700,  # Resize to 700px height
    )

    # Transform the image
    compressed_image = original_image.transform(jpeg_config)
    compressed_bytes = compressed_image.read()

    print(f"Compressed image dimensions: {compressed_image.image.size}")
    print(f"Compressed JPEG size: {len(compressed_bytes)} bytes")
    return compressed_image


def example_default_config():
    """Example 3: Default configuration (1260x700 JPEG with 85 quality)."""
    print("\nExample 3: Default configuration")

    default_maker = ScreenshotMaker()  # Uses default ImageConfig
    default_screenshot = default_maker()

    print(f"Default screenshot dimensions: {default_screenshot.image.size}")
    print(f"Default JPEG size: {len(default_screenshot.read())} bytes")
    return default_screenshot


if __name__ == "__main__":
    example_full_png_screenshot()
    example_default_config()
