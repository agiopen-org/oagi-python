# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image as PILImageLib

from oagi import ImageConfig, PILImage


@pytest.fixture
def mock_rgb_image():
    """Create a mock PIL Image in RGB mode."""
    mock = MagicMock()
    mock.mode = "RGB"
    return mock


@pytest.fixture
def mock_rgba_image():
    """Create a mock PIL Image in RGBA mode."""
    mock = MagicMock()
    mock.mode = "RGBA"
    mock.size = (100, 100)
    mock.split.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    return mock


def assert_save_called_with_format(mock_image, expected_format, expected_quality=None):
    """Helper to verify PIL Image.save was called with expected format and quality."""
    mock_image.save.assert_called_once()
    call_args = mock_image.save.call_args
    assert call_args[1]["format"] == expected_format
    if expected_quality is not None:
        assert call_args[1]["quality"] == expected_quality


class TestPILImageBasics:
    def test_pil_image_converts_to_bytes(self, mock_rgb_image):
        pil_image = PILImage(mock_rgb_image)
        pil_image.read()
        assert_save_called_with_format(mock_rgb_image, "JPEG", 85)

    def test_pil_image_caches_bytes(self, mock_rgb_image):
        pil_image = PILImage(mock_rgb_image)

        first_read = pil_image.read()
        second_read = pil_image.read()

        assert mock_rgb_image.save.call_count == 1
        assert first_read is second_read

    def test_pil_image_jpeg_format(self, mock_rgb_image):
        config = ImageConfig(format="JPEG", quality=70)
        pil_image = PILImage(mock_rgb_image, config)

        pil_image.read()
        assert_save_called_with_format(mock_rgb_image, "JPEG", 70)

    def test_pil_image_rgba_to_rgb_conversion(self, mock_rgba_image):
        config = ImageConfig(format="JPEG")
        pil_image = PILImage(mock_rgba_image, config)

        with patch("oagi.handler.pil_image.PILImageLib.new") as mock_new:
            mock_rgb_image = MagicMock()
            mock_new.return_value = mock_rgb_image

            pil_image.read()

            mock_new.assert_called_once_with("RGB", (100, 100), (255, 255, 255))
            mock_rgb_image.paste.assert_called_once()
            mock_rgb_image.save.assert_called_once()


class TestPILImageFormatConversion:
    @pytest.mark.parametrize(
        "format_name,quality,optimize,expected_signature,color,size",
        [
            ("JPEG", 90, None, b"\xff\xd8\xff", "cyan", (100, 100)),
            ("PNG", None, False, b"\x89PNG\r\n\x1a\n", "magenta", (50, 50)),
            ("PNG", None, True, b"\x89PNG\r\n\x1a\n", "yellow", (40, 40)),
        ],
    )
    def test_convert_format_basic(
        self, format_name, quality, optimize, expected_signature, color, size
    ):
        config_kwargs = {"format": format_name}
        if quality is not None:
            config_kwargs["quality"] = quality
        if optimize is not None:
            config_kwargs["optimize"] = optimize

        config = ImageConfig(**config_kwargs)
        pil_image_obj = PILImage(None, config)
        test_image = PILImageLib.new("RGB", size, color=color)

        converted_bytes = pil_image_obj._convert_format(test_image)

        assert converted_bytes[: len(expected_signature)] == expected_signature
        result = PILImageLib.open(BytesIO(converted_bytes))
        assert result.format == format_name
        assert result.size == size

    def test_convert_format_rgba_to_jpeg(self):
        config = ImageConfig(format="JPEG", quality=80)
        pil_image_obj = PILImage(None, config)
        test_image = PILImageLib.new("RGBA", (60, 60), color=(255, 0, 0, 128))

        jpeg_bytes = pil_image_obj._convert_format(test_image)

        assert jpeg_bytes[:3] == b"\xff\xd8\xff"
        result = PILImageLib.open(BytesIO(jpeg_bytes))
        assert result.format == "JPEG"
        assert result.mode == "RGB"
        assert result.size == (60, 60)

    def test_convert_format_quality_levels(self):
        test_image = PILImageLib.new("RGB", (100, 100), color="orange")
        sizes = []

        for quality in [30, 60, 90]:
            config = ImageConfig(format="JPEG", quality=quality)
            pil_image_obj = PILImage(None, config)
            jpeg_bytes = pil_image_obj._convert_format(test_image)
            sizes.append(len(jpeg_bytes))

        assert sizes[0] <= sizes[2]


class TestPILImageResize:
    def test_pil_image_resize(self):
        config = ImageConfig(width=640, height=480, resample="LANCZOS")
        original = PILImageLib.new("RGB", (1920, 1080), color="blue")
        pil_image = PILImage(original)

        resized = pil_image._resize(original, config)

        assert resized.size == (640, 480)
        assert resized != original

    def test_pil_image_no_resize(self):
        config = ImageConfig(width=None, height=None)
        original = PILImageLib.new("RGB", (1920, 1080), color="green")
        pil_image = PILImage(original)

        result = pil_image._resize(original, config)

        assert result is original
        assert result.size == (1920, 1080)

    @pytest.mark.parametrize(
        "width,height,expected_size",
        [
            (800, None, (800, 1080)),
            (None, 600, (1920, 600)),
        ],
    )
    def test_pil_image_partial_dimensions(self, width, height, expected_size):
        config = ImageConfig(width=width, height=height)
        original = PILImageLib.new("RGB", (1920, 1080), color="red")
        pil_image = PILImage(original)

        resized = pil_image._resize(original, config)
        assert resized.size == expected_size

    @pytest.mark.parametrize(
        "resample_method", ["NEAREST", "BILINEAR", "BICUBIC", "LANCZOS"]
    )
    def test_pil_image_different_resample_methods(self, resample_method):
        config = ImageConfig(width=100, height=100, resample=resample_method)
        original = PILImageLib.new("RGB", (200, 200), color="purple")
        pil_image = PILImage(original)

        resized = pil_image._resize(original, config)
        assert resized.size == (100, 100)


class TestPILImageTransform:
    def test_resize_happens_before_format_conversion(self):
        original_image = PILImageLib.new("RGB", (2000, 1000), color="green")
        config = ImageConfig(width=1260, height=700, format="JPEG", quality=85)

        pil_image = PILImage(original_image)
        transformed = pil_image.transform(config)

        assert transformed.image.size == (1260, 700)

        image_bytes = transformed.read()
        assert image_bytes[:3] == b"\xff\xd8\xff"

        result_image = PILImageLib.open(BytesIO(image_bytes))
        assert result_image.size == (1260, 700)
        assert result_image.format == "JPEG"


class TestPILImageFactoryMethods:
    @patch("oagi.handler.pil_image.PILImageLib.open")
    def test_from_file(self, mock_open):
        mock_image = MagicMock()
        mock_open.return_value = mock_image

        result = PILImage.from_file("/path/to/image.png")

        mock_open.assert_called_once_with("/path/to/image.png")
        assert isinstance(result, PILImage)
        assert result.image is mock_image

    @patch("oagi.handler.pil_image.PILImageLib.open")
    def test_from_bytes(self, mock_open):
        mock_image = MagicMock()
        mock_open.return_value = mock_image
        test_data = b"test image data"

        result = PILImage.from_bytes(test_data)

        mock_open.assert_called_once()
        assert isinstance(result, PILImage)
        assert result.image is mock_image

    @patch("pyautogui.screenshot")
    def test_from_screenshot(self, mock_screenshot):
        mock_image = MagicMock()
        mock_screenshot.return_value = mock_image

        result = PILImage.from_screenshot()

        mock_screenshot.assert_called_once()
        assert isinstance(result, PILImage)
        assert result.image is mock_image
