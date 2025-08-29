# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import MagicMock, patch

from PIL import Image as PILImage

from oagi.screenshot_maker import FileImage, MockImage, ScreenshotImage, ScreenshotMaker


class TestFileImage:
    def test_file_image_reads_file(self, tmp_path):
        # Create a test file
        test_file = tmp_path / "test.png"
        test_data = b"test image data"
        test_file.write_bytes(test_data)

        # Create FileImage and test
        file_image = FileImage(str(test_file))
        assert file_image.read() == test_data

    def test_file_image_caches_data(self, tmp_path):
        # Create a test file
        test_file = tmp_path / "test.png"
        test_data = b"test image data"
        test_file.write_bytes(test_data)

        # Create FileImage
        file_image = FileImage(str(test_file))

        # Read twice - should return same data
        first_read = file_image.read()
        second_read = file_image.read()
        assert first_read is second_read  # Same object reference


class TestMockImage:
    def test_mock_image_returns_mock_data(self):
        mock_image = MockImage()
        assert mock_image.read() == b"mock screenshot data"


class TestScreenshotImage:
    def test_screenshot_image_converts_to_bytes(self):
        # Create a mock PIL Image
        mock_pil_image = MagicMock()

        # Create ScreenshotImage
        screenshot_image = ScreenshotImage(mock_pil_image)

        # Read the image
        screenshot_image.read()

        # Verify save was called with PNG format
        mock_pil_image.save.assert_called_once()
        call_args = mock_pil_image.save.call_args
        assert call_args[1]["format"] == "PNG"

    def test_screenshot_image_caches_bytes(self):
        # Create a mock PIL Image
        mock_pil_image = MagicMock()

        # Create ScreenshotImage
        screenshot_image = ScreenshotImage(mock_pil_image)

        # Read twice
        first_read = screenshot_image.read()
        second_read = screenshot_image.read()

        # Should only save once (cached)
        assert mock_pil_image.save.call_count == 1
        assert first_read is second_read


class TestScreenshotMaker:
    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_maker_takes_screenshot(self, mock_screenshot):
        # Create a mock PIL Image
        mock_pil_image = MagicMock()
        mock_screenshot.return_value = mock_pil_image

        # Create ScreenshotMaker
        maker = ScreenshotMaker()

        # Take a screenshot
        result = maker()

        # Verify screenshot was called
        mock_screenshot.assert_called_once()

        # Verify result is a ScreenshotImage
        assert isinstance(result, ScreenshotImage)
        assert result.screenshot is mock_pil_image

    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_maker_stores_last_screenshot(self, mock_screenshot):
        # Create mock PIL Images
        mock_pil_image1 = MagicMock()
        mock_pil_image2 = MagicMock()
        mock_screenshot.side_effect = [mock_pil_image1, mock_pil_image2]

        # Create ScreenshotMaker
        maker = ScreenshotMaker()

        # Take first screenshot
        first = maker()
        assert maker.last_image() is first

        # Take second screenshot
        second = maker()
        assert maker.last_image() is second
        assert maker.last_image() is not first

    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_maker_last_image_creates_if_none(self, mock_screenshot):
        # Create a mock PIL Image
        mock_pil_image = MagicMock()
        mock_screenshot.return_value = mock_pil_image

        # Create ScreenshotMaker
        maker = ScreenshotMaker()

        # Get last image without taking one first
        result = maker.last_image()

        # Should take a screenshot
        mock_screenshot.assert_called_once()
        assert isinstance(result, ScreenshotImage)

    @patch("oagi.screenshot_maker.pyautogui.screenshot")
    def test_screenshot_image_returns_png_bytes(self, mock_screenshot):
        # Create a real small PIL Image for testing
        pil_image = PILImage.new("RGB", (10, 10), color="red")
        mock_screenshot.return_value = pil_image

        # Create ScreenshotMaker and take screenshot
        maker = ScreenshotMaker()
        screenshot = maker()

        # Get bytes
        image_bytes = screenshot.read()

        # Verify it's PNG data (PNG signature)
        assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"
