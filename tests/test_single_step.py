# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image as PILImageLib

from oagi.single_step import single_step
from oagi.types import Action, ActionType, Image, Step

# Import the module properly

mod = sys.modules["oagi.single_step"]


@pytest.fixture
def mock_task():
    # Patch Task in the module
    with patch.object(mod, "Task") as MockTask:
        mock_instance = Mock()
        MockTask.return_value.__enter__.return_value = mock_instance
        MockTask.return_value.__exit__.return_value = None

        # Setup default step response
        mock_step = Step(
            reason="Need to click the button",
            actions=[
                Action(type=ActionType.CLICK, argument="100, 200", count=1),
                Action(type=ActionType.TYPE, argument="test", count=1),
            ],
            stop=False,
        )
        mock_instance.step.return_value = mock_step

        yield mock_instance, MockTask


class TestSingleStep:
    def test_single_step_with_bytes(self, mock_task):
        mock_instance, MockTask = mock_task

        image_bytes = b"fake image data"

        result = single_step(
            task_description="Fill form",
            screenshot=image_bytes,
            instruction="Use test@example.com",
            api_key="test-key",
            base_url="https://api.example.com",
        )

        assert isinstance(result, Step)
        assert result.reason == "Need to click the button"
        assert len(result.actions) == 2
        assert result.actions[0].type == ActionType.CLICK
        assert not result.stop

        # Verify Task was created with correct params
        MockTask.assert_called_once_with(
            api_key="test-key", base_url="https://api.example.com"
        )

        # Verify init_task and step were called
        mock_instance.init_task.assert_called_once_with("Fill form")
        mock_instance.step.assert_called_once_with(
            image_bytes, instruction="Use test@example.com"
        )

    def test_single_step_with_file_path(self, mock_task, tmp_path):
        mock_instance, MockTask = mock_task

        # Create a valid temporary image file
        image_file = tmp_path / "test.png"
        test_image = PILImageLib.new("RGB", (10, 10), color="red")
        test_image.save(image_file, format="PNG")

        result = single_step(
            task_description="Navigate to settings",
            screenshot=image_file,
        )

        assert isinstance(result, Step)

        # Verify file was read and converted to JPEG bytes (default format)
        call_args = mock_instance.step.call_args[0][0]
        assert call_args[:3] == b"\xff\xd8\xff"  # JPEG signature
        assert mock_instance.step.call_args[1]["instruction"] is None

    def test_single_step_with_path_object(self, mock_task, tmp_path):
        mock_instance, _ = mock_task

        # Create a valid temporary image file
        image_file = tmp_path / "screenshot.png"
        test_image = PILImageLib.new("RGB", (10, 10), color="blue")
        test_image.save(image_file, format="PNG")

        result = single_step(
            task_description="Click button",
            screenshot=Path(image_file),
        )

        assert isinstance(result, Step)

        # Verify Path was handled correctly and converted to JPEG
        call_args = mock_instance.step.call_args[0][0]
        assert call_args[:3] == b"\xff\xd8\xff"  # JPEG signature
        assert mock_instance.step.call_args[1]["instruction"] is None

    def test_single_step_with_string_path(self, mock_task, tmp_path):
        mock_instance, _ = mock_task

        # Create a valid temporary image file
        image_file = tmp_path / "image.png"
        test_image = PILImageLib.new("RGB", (10, 10), color="green")
        test_image.save(image_file, format="PNG")

        result = single_step(
            task_description="Test task",
            screenshot=str(image_file),
        )

        assert isinstance(result, Step)

        # Verify string path was handled correctly and converted to JPEG
        call_args = mock_instance.step.call_args[0][0]
        assert call_args[:3] == b"\xff\xd8\xff"  # JPEG signature
        assert mock_instance.step.call_args[1]["instruction"] is None

    def test_single_step_with_nonexistent_file_raises_error(self, mock_task):
        with pytest.raises(FileNotFoundError, match="Screenshot file not found"):
            single_step(
                task_description="Test task",
                screenshot="nonexistent/file.png",
            )

    def test_single_step_with_image_object(self, mock_task):
        mock_instance, _ = mock_task

        # Create a mock Image object
        mock_image = Mock(spec=Image)
        mock_image.read.return_value = b"image bytes from Image"

        result = single_step(
            task_description="Test with Image",
            screenshot=mock_image,
        )

        assert isinstance(result, Step)

        # Verify Image.read() was called and bytes were passed
        mock_image.read.assert_called_once()
        mock_instance.step.assert_called_once_with(
            b"image bytes from Image", instruction=None
        )

    def test_single_step_uses_image_read(self, mock_task):
        mock_instance, _ = mock_task

        # Create a mock Image object
        mock_image = Mock(spec=Image)
        mock_image.read.return_value = b"image data"

        single_step(
            task_description="Test task",
            screenshot=mock_image,
        )

        # Verify Image.read() was called
        mock_image.read.assert_called_once()
        mock_instance.step.assert_called_once_with(b"image data", instruction=None)

    def test_single_step_invalid_screenshot_type(self):
        with pytest.raises(
            ValueError, match="screenshot must be Image, bytes, str, or Path"
        ):
            single_step(
                task_description="Test",
                screenshot=123,  # Invalid type
            )

    def test_single_step_with_instruction(self, mock_task):
        mock_instance, _ = mock_task

        single_step(
            task_description="Fill form",
            screenshot=b"data",
            instruction="Use specific values",
        )

        mock_instance.step.assert_called_once_with(
            b"data", instruction="Use specific values"
        )
