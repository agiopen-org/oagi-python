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

from oagi import ImageConfig, PILImage, ScreenshotMaker


@pytest.fixture
def mock_screenshot_image():
    """Create a mock PIL Image for screenshot tests."""
    mock = MagicMock()
    mock.width = 1920
    mock.height = 1080
    mock_resized = MagicMock()
    mock.resize.return_value = mock_resized
    return mock, mock_resized


class TestScreenshotMaker:
    @patch("pyautogui.screenshot")
    def test_screenshot_maker_takes_screenshot(
        self, mock_screenshot, mock_screenshot_image
    ):
        mock_pil_image, mock_resized_image = mock_screenshot_image
        mock_screenshot.return_value = mock_pil_image

        maker = ScreenshotMaker()
        result = maker()

        mock_screenshot.assert_called_once()
        mock_pil_image.resize.assert_called_once_with((1260, 700), PILImageLib.LANCZOS)
        assert isinstance(result, PILImage)
        assert result.image is mock_resized_image

    @patch("pyautogui.screenshot")
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

    @patch("pyautogui.screenshot")
    def test_screenshot_maker_last_image_creates_if_none(
        self, mock_screenshot, mock_screenshot_image
    ):
        mock_pil_image, mock_resized = mock_screenshot_image
        mock_screenshot.return_value = mock_pil_image

        maker = ScreenshotMaker()
        result = maker.last_image()

        mock_screenshot.assert_called_once()
        assert isinstance(result, PILImage)

    @patch("pyautogui.screenshot")
    def test_screenshot_image_returns_png_bytes(self, mock_screenshot):
        pil_image = PILImageLib.new("RGB", (10, 10), color="red")
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
    @patch("pyautogui.screenshot")
    def test_screenshot_maker_resize_dimensions(
        self, mock_screenshot, mock_screenshot_image, width, height, expected_size
    ):
        mock_pil_image, mock_resized_image = mock_screenshot_image
        mock_screenshot.return_value = mock_pil_image

        config = ImageConfig(width=width, height=height)
        maker = ScreenshotMaker(config=config)
        result = maker()

        mock_pil_image.resize.assert_called_once_with(
            expected_size, PILImageLib.LANCZOS
        )
        assert isinstance(result, PILImage)
        assert result.image is mock_resized_image

    @pytest.mark.parametrize(
        "format_name,expected_signature",
        [
            ("JPEG", b"\xff\xd8\xff"),
            ("PNG", b"\x89PNG\r\n\x1a\n"),
        ],
    )
    @patch("pyautogui.screenshot")
    def test_screenshot_maker_format_output(
        self, mock_screenshot, format_name, expected_signature
    ):
        pil_image = PILImageLib.new("RGB", (10, 10), color="blue")
        mock_screenshot.return_value = pil_image

        config = ImageConfig(format=format_name, width=None, height=None)
        maker = ScreenshotMaker(config=config)
        screenshot = maker()

        image_bytes = screenshot.read()
        assert image_bytes[: len(expected_signature)] == expected_signature

        result_image = PILImageLib.open(BytesIO(image_bytes))
        assert result_image.format == format_name

    @patch("pyautogui.screenshot")
    def test_screenshot_maker_default_resize_1260x700(
        self, mock_screenshot, mock_screenshot_image
    ):
        mock_pil_image, mock_resized_image = mock_screenshot_image
        mock_pil_image.width = 2560
        mock_pil_image.height = 1440
        mock_screenshot.return_value = mock_pil_image

        maker = ScreenshotMaker()
        result = maker()

        mock_pil_image.resize.assert_called_once_with((1260, 700), PILImageLib.LANCZOS)
        assert isinstance(result, PILImage)
        assert result.image is mock_resized_image

    @patch("pyautogui.screenshot")
    def test_resize_happens_before_format_conversion(self, mock_screenshot):
        original_image = PILImageLib.new("RGB", (2000, 1000), color="green")
        mock_screenshot.return_value = original_image

        config = ImageConfig(width=1260, height=700, format="JPEG", quality=85)
        maker = ScreenshotMaker(config=config)
        screenshot = maker()

        assert screenshot.image.size == (1260, 700)

        image_bytes = screenshot.read()
        assert image_bytes[:3] == b"\xff\xd8\xff"

        result_image = PILImageLib.open(BytesIO(image_bytes))
        assert result_image.size == (1260, 700)
        assert result_image.format == "JPEG"
