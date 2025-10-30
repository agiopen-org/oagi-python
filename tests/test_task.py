# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import patch

import pytest

from oagi.task import Task
from oagi.types import ActionType, Step


@pytest.fixture
def task(mock_sync_client):
    """Create a Task instance with mocked client."""
    return Task(api_key="test-key", base_url="https://test.example.com")


class TestTaskInit:
    def test_init_with_parameters(self, mock_sync_client):
        task = Task(api_key="test-key", base_url="https://test.example.com")
        assert task.api_key == "test-key"
        assert task.base_url == "https://test.example.com"
        assert task.task_id is None
        assert task.task_description is None
        assert task.model == "vision-model-v1"

    def test_init_with_custom_model(self, mock_sync_client):
        task = Task(
            api_key="test-key",
            base_url="https://test.example.com",
            model="custom-model",
        )
        assert task.model == "custom-model"

    def test_init_with_env_vars(self, mock_sync_client):
        with patch.dict(
            "os.environ",
            {"OAGI_BASE_URL": "https://env.example.com", "OAGI_API_KEY": "env-key"},
        ):
            mock_sync_client.api_key = "env-key"
            mock_sync_client.base_url = "https://env.example.com"
            task = Task()
            assert task.api_key == "env-key"
            assert task.base_url == "https://env.example.com"

    def test_init_parameters_override_env_vars(self, mock_sync_client):
        with patch.dict(
            "os.environ",
            {"OAGI_BASE_URL": "https://env.example.com", "OAGI_API_KEY": "env-key"},
        ):
            task = Task(api_key="override-key", base_url="https://override.example.com")
            assert task.api_key == "test-key"  # From mock_sync_client
            assert task.base_url == "https://test.example.com"  # From mock_sync_client


class TestInitTask:
    def test_init_task_success(self, task, sample_llm_response):
        task.client.create_message.return_value = sample_llm_response

        task.init_task("Test task description", max_steps=10)

        assert task.task_description == "Test task description"
        assert task.task_id == "task-456"

        task.client.create_message.assert_called_once_with(
            model="vision-model-v1",
            screenshot="",
            task_description="Test task description",
            task_id=None,
        )

    def test_init_task_resets_task_id(self, task, sample_llm_response):
        # Set existing task_id
        task.task_id = "old-task-123"
        task.client.create_message.return_value = sample_llm_response

        task.init_task("New task")

        assert task.task_id == "task-456"  # New task_id from response


class TestStep:
    def test_step_with_image_object(self, task, mock_image, sample_llm_response):
        task.task_description = "Test task"
        task.task_id = "existing-task"
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded_image"

            result = task.step(mock_image)

            # Verify Image.read() was called
            mock_image.read.assert_called_once()

            # Verify encoding was called with image bytes
            mock_encode.assert_called_once_with(b"fake image bytes")

            # Verify API call
            task.client.create_message.assert_called_once_with(
                model="vision-model-v1",
                screenshot="base64_encoded_image",
                task_description="Test task",
                task_id="existing-task",
                instruction=None,
                last_task_id=None,
                history_steps=None,
            )

            # Verify returned Step
            assert isinstance(result, Step)
            assert result.reason == "Need to click button and type text"
            assert len(result.actions) == 2
            assert result.actions[0].type == ActionType.CLICK
            assert result.actions[1].type == ActionType.TYPE
            assert result.stop is False

    def test_step_with_bytes_directly(self, task, sample_llm_response):
        task.task_description = "Test task"
        task.task_id = None
        task.client.create_message.return_value = sample_llm_response

        image_bytes = b"raw image bytes"

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded_bytes"

            result = task.step(image_bytes)

            # Verify encoding was called directly with bytes
            mock_encode.assert_called_once_with(image_bytes)

            # Verify API call
            task.client.create_message.assert_called_once_with(
                model="vision-model-v1",
                screenshot="base64_encoded_bytes",
                task_description="Test task",
                task_id=None,
                instruction=None,
                last_task_id=None,
                history_steps=None,
            )

            # Verify task_id was updated
            assert task.task_id == "task-456"

            # Verify returned Step
            assert isinstance(result, Step)
            assert result.stop is False

    def test_step_without_init_task_raises_error(self, task):
        with pytest.raises(
            ValueError, match="Task description must be set. Call init_task\\(\\) first"
        ):
            task.step(b"image bytes")

    def test_step_with_completed_response(self, task, completed_llm_response):
        task.task_description = "Test task"
        task.task_id = "task-456"
        task.client.create_message.return_value = completed_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            result = task.step(b"image bytes")

            assert result.stop is True
            assert result.reason == "Task completed successfully"
            assert len(result.actions) == 0

    def test_step_updates_changed_task_id(self, task, sample_llm_response):
        task.task_description = "Test task"
        task.task_id = "old-task-id"
        sample_llm_response.task_id = "new-task-id"
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            task.step(b"image bytes")

            assert task.task_id == "new-task-id"

    def test_step_handles_exception(self, task):
        task.task_description = "Test task"
        task.client.create_message.side_effect = Exception("API Error")

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            with pytest.raises(Exception, match="API Error"):
                task.step(b"image bytes")

    def test_step_with_instruction(self, task, sample_llm_response):
        task.task_description = "Test task"
        task.task_id = "existing-task"
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            result = task.step(b"image bytes", instruction="Click the submit button")

            # Verify API call includes instruction
            task.client.create_message.assert_called_once_with(
                model="vision-model-v1",
                screenshot="base64_encoded",
                task_description="Test task",
                task_id="existing-task",
                instruction="Click the submit button",
                last_task_id=None,
                history_steps=None,
            )

            assert isinstance(result, Step)
            assert not result.stop


class TestContextManager:
    def test_context_manager(self, mock_sync_client):
        with Task(api_key="test-key", base_url="https://test.example.com") as task:
            assert task.api_key == "test-key"
            assert task.base_url == "https://test.example.com"

        # Verify close was called
        mock_sync_client.close.assert_called_once()

    def test_close_method(self, task):
        task.close()
        task.client.close.assert_called_once()

    def test_context_manager_with_exception(self, mock_sync_client):
        try:
            with Task(api_key="test-key", base_url="https://test.example.com"):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify close was still called despite exception
        mock_sync_client.close.assert_called_once()


class TestIntegrationScenarios:
    def test_full_workflow(self, task, sample_llm_response, completed_llm_response):
        """Test a complete workflow from init to completion."""
        # Initialize task
        task.client.create_message.return_value = sample_llm_response
        task.init_task("Complete workflow test")

        assert task.task_id == "task-456"
        assert task.task_description == "Complete workflow test"

        # First step - in progress
        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            step1 = task.step(b"screenshot1")
            assert not step1.stop
            assert len(step1.actions) == 2

            # Second step - completed
            task.client.create_message.return_value = completed_llm_response
            step2 = task.step(b"screenshot2")
            assert step2.stop
            assert len(step2.actions) == 0

    def test_task_id_persistence_across_steps(self, task, sample_llm_response):
        """Test that task_id is maintained across multiple steps."""
        task.task_description = "Test task"
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            # First step - sets task_id
            task.step(b"screenshot1")
            assert task.task_id == "task-456"

            # Second step - uses same task_id
            task.step(b"screenshot2")

            # Verify second call used the task_id
            calls = task.client.create_message.call_args_list
            assert calls[1][1]["task_id"] == "task-456"


class TestTaskHistory:
    """Test Task class history functionality."""

    def test_init_task_with_history(self, task, sample_llm_response):
        """Test init_task with history parameters."""
        task.client.create_message.return_value = sample_llm_response

        # Initialize task with history
        task.init_task(
            "Test task",
            max_steps=5,
            last_task_id="previous-task",
            history_steps=2,
        )

        # Verify task attributes
        assert task.task_description == "Test task"
        assert task.task_id == "task-456"
        assert task.last_task_id == "previous-task"
        assert task.history_steps == 2

        # History is not sent during init, only stored
        task.client.create_message.assert_called_once_with(
            model="vision-model-v1",
            screenshot="",
            task_description="Test task",
            task_id=None,
        )

    def test_init_task_without_history(self, task, sample_llm_response):
        """Test init_task without history parameters."""
        task.client.create_message.return_value = sample_llm_response

        # Initialize task without history
        task.init_task("Test task", max_steps=5)

        # Verify task attributes
        assert task.task_description == "Test task"
        assert task.task_id == "task-456"
        assert task.last_task_id is None
        assert task.history_steps is None

    def test_step_with_history(self, task, sample_llm_response):
        """Test step method with history (continuing session)."""
        task.task_description = "Test task"
        task.task_id = "task-456"  # Already have task_id
        task.last_task_id = "previous-task"
        task.history_steps = 2
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            # Call step
            task.step(b"screenshot_data", instruction="Click submit")

            # Verify API call includes history params
            task.client.create_message.assert_called_once_with(
                model="vision-model-v1",
                screenshot="base64_encoded",
                task_description="Test task",
                task_id="task-456",
                instruction="Click submit",
                last_task_id="previous-task",
                history_steps=2,
            )

    def test_step_history_only_when_continuing(self, task, sample_llm_response):
        """Test that history is only sent when continuing (task_id exists)."""
        task.task_description = "Test task"
        task.last_task_id = "previous-task"
        task.history_steps = 1
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            # First step - no task_id yet
            task.task_id = None
            task.step(b"screenshot1")

            # Verify first call - no history
            first_call = task.client.create_message.call_args_list[0][1]
            assert first_call["task_id"] is None
            assert first_call["last_task_id"] is None
            assert first_call["history_steps"] is None

            # Task ID should be updated
            assert task.task_id == "task-456"

            # Second step - now have task_id
            task.step(b"screenshot2")

            # Verify second call - includes history
            second_call = task.client.create_message.call_args_list[1][1]
            assert second_call["task_id"] == "task-456"
            assert second_call["last_task_id"] == "previous-task"
            assert second_call["history_steps"] == 1

    def test_init_task_with_default_history_steps(self, task, sample_llm_response):
        """Test that history_steps can be omitted."""
        task.client.create_message.return_value = sample_llm_response

        # Initialize task with last_task_id but no history_steps
        task.init_task(
            "Test task",
            max_steps=5,
            last_task_id="previous-task",
            # history_steps not specified
        )

        # Verify task attributes
        assert task.last_task_id == "previous-task"
        assert task.history_steps is None  # Not specified

    def test_step_without_history(self, task, sample_llm_response):
        """Test step method without history (first step)."""
        task.task_description = "Test task"
        task.task_id = None  # First step
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            # Call step
            result = task.step(b"screenshot_data")

            # Verify API call - no history params on first step
            task.client.create_message.assert_called_once_with(
                model="vision-model-v1",
                screenshot="base64_encoded",
                task_description="Test task",
                task_id=None,
                instruction=None,
                last_task_id=None,
                history_steps=None,
            )

            # Verify result
            assert isinstance(result, Step)
            assert not result.stop
            assert len(result.actions) == 2


class TestTaskTemperature:
    def test_task_with_default_temperature(self, mock_sync_client, sample_llm_response):
        """Test that task uses default temperature when provided."""
        task = Task(
            api_key="test-key",
            base_url="https://test.example.com",
            temperature=0.5,
        )
        task.task_description = "Test task"
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            task.step(b"screenshot_data")

            # Verify temperature is passed to create_message
            call_args = task.client.create_message.call_args
            assert call_args[1]["temperature"] == 0.5

    def test_step_temperature_overrides_task_default(
        self, mock_sync_client, sample_llm_response
    ):
        """Test that step temperature overrides task default."""
        task = Task(
            api_key="test-key",
            base_url="https://test.example.com",
            temperature=0.5,
        )
        task.task_description = "Test task"
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            # Call step with different temperature
            task.step(b"screenshot_data", temperature=0.9)

            # Verify step temperature (0.9) is used, not task default (0.5)
            call_args = task.client.create_message.call_args
            assert call_args[1]["temperature"] == 0.9

    def test_step_without_any_temperature(self, mock_sync_client, sample_llm_response):
        """Test that when no temperature is provided, None is passed."""
        task = Task(api_key="test-key", base_url="https://test.example.com")
        task.task_description = "Test task"
        task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            task.step(b"screenshot_data")

            # Verify temperature is None (worker will use its default)
            call_args = task.client.create_message.call_args
            assert call_args[1]["temperature"] is None
