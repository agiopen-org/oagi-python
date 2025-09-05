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
from PIL import Image as PILImage

from oagi import ImageConfig
from oagi.screenshot_maker import FileImage, MockImage, ScreenshotImage, ScreenshotMaker


@pytest.fixture
def test_image_file(tmp_path):
    """Create a test image file with known data."""
    test_file = tmp_path / "test.png"
    test_data = b"test image data"
    test_file.write_bytes(test_data)
    return str(test_file), test_data


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


@pytest.fixture
def mock_screenshot_image():
    """Create a mock PIL Image for screenshot tests."""
    mock = MagicMock()
    mock.width = 1920
    mock.height = 1080
    mock_resized = MagicMock()
    mock.resize.return_value = mock_resized
    return mock, mock_resized


def assert_save_called_with_format(mock_image, expected_format, expected_quality=None):
    """Helper to verify PIL Image.save was called with expected format and quality."""
    mock_image.save.assert_called_once()
    call_args = mock_image.save.call_args
    assert call_args[1]["format"] == expected_format
    if expected_quality is not None:
        assert call_args[1]["quality"] == expected_quality


class TestFileImage:
    def test_file_image_reads_file(self, test_image_file):
        file_path, expected_data = test_image_file
        file_image = FileImage(file_path)
        assert file_image.read() == expected_data

    def test_file_image_caches_data(self, test_image_file):
        file_path, _ = test_image_file
        file_image = FileImage(file_path)

        first_read = file_image.read()
        second_read = file_image.read()
        assert first_read is second_read


class TestMockImage:
    def test_mock_image_returns_mock_data(self):
        mock_image = MockImage()
        assert mock_image.read() == b"mock screenshot data"


class TestScreenshotImage:
    def test_screenshot_image_converts_to_bytes(self, mock_rgb_image):
        screenshot_image = ScreenshotImage(mock_rgb_image)
        screenshot_image.read()
        assert_save_called_with_format(mock_rgb_image, "JPEG", 85)

    def test_screenshot_image_caches_bytes(self, mock_rgb_image):
        screenshot_image = ScreenshotImage(mock_rgb_image)

        first_read = screenshot_image.read()
        second_read = screenshot_image.read()

        assert mock_rgb_image.save.call_count == 1
        assert first_read is second_read

    def test_screenshot_image_jpeg_format(self, mock_rgb_image):
        config = ImageConfig(format="JPEG", quality=70)
        screenshot_image = ScreenshotImage(mock_rgb_image, config)

        screenshot_image.read()
        assert_save_called_with_format(mock_rgb_image, "JPEG", 70)

    def test_screenshot_image_rgba_to_rgb_conversion(self, mock_rgba_image):
        config = ImageConfig(format="JPEG")
        screenshot_image = ScreenshotImage(mock_rgba_image, config)

        with patch("oagi.screenshot_maker.PILImage.new") as mock_new:
            mock_rgb_image = MagicMock()
            mock_new.return_value = mock_rgb_image

            screenshot_image.read()

            mock_new.assert_called_once_with("RGB", (100, 100), (255, 255, 255))
            mock_rgb_image.paste.assert_called_once()
            mock_rgb_image.save.assert_called_once()

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
        screenshot_image = ScreenshotImage(None, config)
        test_image = PILImage.new("RGB", size, color=color)

        converted_bytes = screenshot_image._convert_format(test_image)

        assert converted_bytes[: len(expected_signature)] == expected_signature
        result = PILImage.open(BytesIO(converted_bytes))
        assert result.format == format_name
        assert result.size == size

    def test_convert_format_rgba_to_jpeg(self):
        config = ImageConfig(format="JPEG", quality=80)
        screenshot_image = ScreenshotImage(None, config)
        test_image = PILImage.new("RGBA", (60, 60), color=(255, 0, 0, 128))

        jpeg_bytes = screenshot_image._convert_format(test_image)

        assert jpeg_bytes[:3] == b"\xff\xd8\xff"
        result = PILImage.open(BytesIO(jpeg_bytes))
        assert result.format == "JPEG"
        assert result.mode == "RGB"
        assert result.size == (60, 60)

    def test_convert_format_quality_levels(self):
        test_image = PILImage.new("RGB", (100, 100), color="orange")
        sizes = []

        for quality in [30, 60, 90]:
            config = ImageConfig(format="JPEG", quality=quality)
            screenshot_image = ScreenshotImage(None, config)
            jpeg_bytes = screenshot_image._convert_format(test_image)
            sizes.append(len(jpeg_bytes))

        assert sizes[0] <= sizes[2]


class TestScreenshotMaker:
    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_maker_takes_screenshot(
        self, mock_screenshot, mock_screenshot_image
    ):
        mock_pil_image, mock_resized_image = mock_screenshot_image
        mock_screenshot.return_value = mock_pil_image

        maker = ScreenshotMaker()
        result = maker()

        mock_screenshot.assert_called_once()
        mock_pil_image.resize.assert_called_once_with((1260, 700), PILImage.LANCZOS)
        assert isinstance(result, ScreenshotImage)
        assert result.screenshot is mock_resized_image

    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_maker_stores_last_screenshot(self, mock_screenshot):
        def create_mock_image():
            mock = MagicMock()
            mock.width = 1920
            mock.height = 1080
            mock_resized = MagicMock()
            mock.resize.return_value = mock_resized
            return mock

        mock_pil_image1 = create_mock_image()
        mock_pil_image2 = create_mock_image()
        mock_screenshot.side_effect = [mock_pil_image1, mock_pil_image2]

        config = ImageConfig(width=None, height=None)
        maker = ScreenshotMaker(config=config)

        first = maker()
        assert maker.last_image() is first

        second = maker()
        assert maker.last_image() is second
        assert maker.last_image() is not first

    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_maker_last_image_creates_if_none(
        self, mock_screenshot, mock_screenshot_image
    ):
        mock_pil_image, mock_resized = mock_screenshot_image
        mock_screenshot.return_value = mock_pil_image

        maker = ScreenshotMaker()
        result = maker.last_image()

        mock_screenshot.assert_called_once()
        assert isinstance(result, ScreenshotImage)

    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_image_returns_png_bytes(self, mock_screenshot):
        pil_image = PILImage.new("RGB", (10, 10), color="red")
        mock_screenshot.return_value = pil_image

        config = ImageConfig(format="PNG")
        maker = ScreenshotMaker(config=config)
        screenshot = maker()

        image_bytes = screenshot.read()
        assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.parametrize(
        "width,height,expected_size",
        [
            (1280, 720, (1280, 720)),
            (1280, None, (1280, 1080)),  # Uses original height
            (None, 600, (1920, 600)),  # Uses original width
        ],
    )
    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_maker_resize_dimensions(
        self, mock_screenshot, mock_screenshot_image, width, height, expected_size
    ):
        mock_pil_image, mock_resized_image = mock_screenshot_image
        mock_screenshot.return_value = mock_pil_image

        config = ImageConfig(width=width, height=height)
        maker = ScreenshotMaker(config=config)
        result = maker()

        mock_pil_image.resize.assert_called_once_with(expected_size, PILImage.LANCZOS)
        assert isinstance(result, ScreenshotImage)
        assert result.screenshot is mock_resized_image

    @pytest.mark.parametrize(
        "format_name,expected_signature",
        [
            ("JPEG", b"\xff\xd8\xff"),
            ("PNG", b"\x89PNG\r\n\x1a\n"),
        ],
    )
    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_maker_format_output(
        self, mock_screenshot, format_name, expected_signature
    ):
        pil_image = PILImage.new("RGB", (10, 10), color="blue")
        mock_screenshot.return_value = pil_image

        config = ImageConfig(format=format_name, width=None, height=None)
        maker = ScreenshotMaker(config=config)
        screenshot = maker()

        image_bytes = screenshot.read()
        assert image_bytes[: len(expected_signature)] == expected_signature

        result_image = PILImage.open(BytesIO(image_bytes))
        assert result_image.format == format_name

    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_maker_default_resize_1260x700(
        self, mock_screenshot, mock_screenshot_image
    ):
        mock_pil_image, mock_resized_image = mock_screenshot_image
        mock_pil_image.width = 2560
        mock_pil_image.height = 1440
        mock_screenshot.return_value = mock_pil_image

        maker = ScreenshotMaker()
        result = maker()

        mock_pil_image.resize.assert_called_once_with((1260, 700), PILImage.LANCZOS)
        assert isinstance(result, ScreenshotImage)
        assert result.screenshot is mock_resized_image

    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_resize_happens_before_format_conversion(self, mock_screenshot):
        original_image = PILImage.new("RGB", (2000, 1000), color="green")
        mock_screenshot.return_value = original_image

        config = ImageConfig(width=1260, height=700, format="JPEG", quality=85)
        maker = ScreenshotMaker(config=config)
        screenshot = maker()

        assert screenshot.screenshot.size == (1260, 700)

        image_bytes = screenshot.read()
        assert image_bytes[:3] == b"\xff\xd8\xff"

        result_image = PILImage.open(BytesIO(image_bytes))
        assert result_image.size == (1260, 700)
        assert result_image.format == "JPEG"

    def test_resize_image_method(self):
        config = ImageConfig(width=640, height=480, resample="LANCZOS")
        maker = ScreenshotMaker(config=config)
        original = PILImage.new("RGB", (1920, 1080), color="blue")

        resized = maker._resize_image(original)

        assert resized.size == (640, 480)
        assert resized != original

    def test_resize_image_method_no_resize(self):
        config = ImageConfig(width=None, height=None)
        maker = ScreenshotMaker(config=config)
        original = PILImage.new("RGB", (1920, 1080), color="green")

        result = maker._resize_image(original)

        assert result is original
        assert result.size == (1920, 1080)

    @pytest.mark.parametrize(
        "width,height,expected_size",
        [
            (800, None, (800, 1080)),
            (None, 600, (1920, 600)),
        ],
    )
    def test_resize_image_partial_dimensions(self, width, height, expected_size):
        config = ImageConfig(width=width, height=height)
        maker = ScreenshotMaker(config=config)
        original = PILImage.new("RGB", (1920, 1080), color="red")

        resized = maker._resize_image(original)
        assert resized.size == expected_size

    @pytest.mark.parametrize(
        "resample_method", ["NEAREST", "BILINEAR", "BICUBIC", "LANCZOS"]
    )
    def test_resize_image_different_resample_methods(self, resample_method):
        config = ImageConfig(width=100, height=100, resample=resample_method)
        maker = ScreenshotMaker(config=config)
        original = PILImage.new("RGB", (200, 200), color="purple")

        resized = maker._resize_image(original)
        assert resized.size == (100, 100)
