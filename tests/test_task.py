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
from oagi.types.models import LLMResponse


@pytest.fixture
def task(mock_sync_client):
    """Create a Task instance with mocked client."""
    return Task(api_key="test-key", base_url="https://test.example.com")


class TestTaskInit:
    def test_init_with_parameters(self, mock_sync_client):
        task = Task(api_key="test-key", base_url="https://test.example.com")
        assert task.api_key == "test-key"
        assert task.base_url == "https://test.example.com"
        # V2 API: task_id is generated as UUID on init
        assert task.task_id is not None
        assert isinstance(task.task_id, str)
        assert len(task.task_id) == 32  # UUID hex without dashes
        assert task.task_description is None
        assert task.model == "vision-model-v1"
        assert task.message_history == []

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
        # V2 API: init_task() no longer makes API call, just sets description
        original_task_id = task.task_id

        task.init_task("Test task description", max_steps=10)

        assert task.task_description == "Test task description"
        # V2 API: task_id doesn't change after init_task
        assert task.task_id == original_task_id

        # V2 API: No API call in init_task
        task.client.create_message.assert_not_called()


class TestStep:
    def test_step_with_image_object(self, task, mock_image, sample_llm_response):
        task.task_description = "Test task"
        task.task_id = "existing-task"
        task.client.create_message.return_value = sample_llm_response

        result = task.step(mock_image)

        # Verify Image.read() was called
        mock_image.read.assert_called_once()

        # Verify API call - V2 uses bytes directly, messages_history instead of last_task_id/history_steps
        call_args = task.client.create_message.call_args
        assert call_args[1]["model"] == "vision-model-v1"
        assert call_args[1]["screenshot"] == b"fake image bytes"
        assert call_args[1]["task_description"] == "Test task"
        assert call_args[1]["task_id"] == "existing-task"
        assert call_args[1]["instruction"] is None
        assert (
            "messages_history" in call_args[1]
        )  # History is passed (tested in TestTaskHistory)
        assert call_args[1]["temperature"] is None

        # Verify returned Step
        assert isinstance(result, Step)
        assert result.reason == "Need to click button and type text"
        assert len(result.actions) == 2
        assert result.actions[0].type == ActionType.CLICK
        assert result.actions[1].type == ActionType.TYPE
        assert result.stop is False

        # V2 API: Verify message_history was updated with assistant response
        assert len(task.message_history) == 1
        assert task.message_history[0]["role"] == "assistant"

    def test_step_with_bytes_directly(self, task, sample_llm_response):
        task.task_description = "Test task"
        original_task_id = task.task_id
        task.client.create_message.return_value = sample_llm_response

        image_bytes = b"raw image bytes"

        result = task.step(image_bytes)

        # Verify API call - V2 uses bytes directly
        call_args = task.client.create_message.call_args
        assert call_args[1]["model"] == "vision-model-v1"
        assert call_args[1]["screenshot"] == image_bytes
        assert call_args[1]["task_description"] == "Test task"
        assert call_args[1]["task_id"] == original_task_id
        assert call_args[1]["instruction"] is None
        assert "messages_history" in call_args[1]
        assert call_args[1]["temperature"] is None

        # V2 API: task_id doesn't change (stays same UUID)
        assert task.task_id == original_task_id

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

        result = task.step(b"image bytes")

        assert result.stop is True
        assert result.reason == "Task completed successfully"
        assert len(result.actions) == 0

    def test_step_updates_changed_task_id(self, task, sample_llm_response):
        # V2 API: task_id is client-side UUID and doesn't change
        task.task_description = "Test task"
        original_task_id = task.task_id
        task.client.create_message.return_value = sample_llm_response

        task.step(b"image bytes")

        # V2 API: task_id stays the same
        assert task.task_id == original_task_id

    def test_step_handles_exception(self, task):
        task.task_description = "Test task"
        task.client.create_message.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            task.step(b"image bytes")

    def test_step_with_instruction(self, task, sample_llm_response):
        task.task_description = "Test task"
        task.task_id = "existing-task"
        task.client.create_message.return_value = sample_llm_response

        result = task.step(b"image bytes", instruction="Click the submit button")

        # Verify API call includes instruction
        call_args = task.client.create_message.call_args
        assert call_args[1]["model"] == "vision-model-v1"
        assert call_args[1]["screenshot"] == b"image bytes"
        assert call_args[1]["task_description"] == "Test task"
        assert call_args[1]["task_id"] == "existing-task"
        assert call_args[1]["instruction"] == "Click the submit button"
        assert "messages_history" in call_args[1]
        assert call_args[1]["temperature"] is None

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
        # Initialize task - V2 doesn't make API call
        task.init_task("Complete workflow test")
        original_task_id = task.task_id

        assert task.task_description == "Complete workflow test"

        # First step - in progress
        task.client.create_message.return_value = sample_llm_response
        step1 = task.step(b"screenshot1")
        assert not step1.stop
        assert len(step1.actions) == 2
        # V2: task_id stays the same
        assert task.task_id == original_task_id

        # Second step - completed
        task.client.create_message.return_value = completed_llm_response
        step2 = task.step(b"screenshot2")
        assert step2.stop
        assert len(step2.actions) == 0
        assert task.task_id == original_task_id

    def test_task_id_persistence_across_steps(self, task, sample_llm_response):
        """Test that task_id is maintained across multiple steps (V2 uses UUID)."""
        task.task_description = "Test task"
        original_task_id = task.task_id
        task.client.create_message.return_value = sample_llm_response

        # First step
        task.step(b"screenshot1")
        assert task.task_id == original_task_id

        # Second step - uses same task_id
        task.step(b"screenshot2")

        # Verify both calls used the same task_id
        calls = task.client.create_message.call_args_list
        assert calls[0][1]["task_id"] == original_task_id
        assert calls[1][1]["task_id"] == original_task_id


class TestTaskHistory:
    """Test Task class message history functionality (V2 API)."""

    def test_init_task_initializes_empty_history(self, task):
        """Test that init_task starts with empty message history."""
        task.init_task("Test task", max_steps=5)

        # V2 API: message_history starts empty
        assert task.message_history == []
        assert task.task_description == "Test task"

    def test_step_updates_message_history(self, task, sample_llm_response):
        """Test that step updates message_history with assistant response."""
        task.task_description = "Test task"
        task.client.create_message.return_value = sample_llm_response

        # First step
        task.step(b"screenshot1")

        # Verify message_history was updated with assistant response
        assert len(task.message_history) == 1
        assert task.message_history[0]["role"] == "assistant"
        assert "content" in task.message_history[0]
        assert task.message_history[0]["content"][0]["type"] == "text"

    def test_step_accumulates_history_across_steps(self, task, sample_llm_response):
        """Test that message_history accumulates across multiple steps."""
        task.task_description = "Test task"
        task.client.create_message.return_value = sample_llm_response

        # First step
        task.step(b"screenshot1")
        assert len(task.message_history) == 1

        # Second step
        task.step(b"screenshot2")
        assert len(task.message_history) == 2

        # Both should be assistant messages
        assert all(msg["role"] == "assistant" for msg in task.message_history)

    def test_step_sends_accumulated_history(self, task, sample_llm_response):
        """Test that step sends accumulated message_history to API."""
        task.task_description = "Test task"
        task.client.create_message.return_value = sample_llm_response

        # Add some history manually
        existing_history = [
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "Previous response"}],
            }
        ]
        task.message_history = existing_history.copy()

        # Capture history length before the call
        history_len_before = len(task.message_history)

        # Call step
        task.step(b"screenshot_data")

        # Verify message_history was passed and then updated (should be longer now)
        assert len(task.message_history) == history_len_before + 1
        assert task.message_history[0] == existing_history[0]  # Old history preserved

    def test_step_without_history(self, task, sample_llm_response):
        """Test step method on first interaction (no history yet)."""
        task.task_description = "Test task"
        task_id = task.task_id
        task.client.create_message.return_value = sample_llm_response

        # Verify history is empty before the call
        assert len(task.message_history) == 0

        result = task.step(b"screenshot_data")

        # Verify API call was made
        call_args = task.client.create_message.call_args
        assert call_args[1]["model"] == "vision-model-v1"
        assert call_args[1]["screenshot"] == b"screenshot_data"
        assert call_args[1]["task_description"] == "Test task"
        assert call_args[1]["task_id"] == task_id
        assert call_args[1]["instruction"] is None
        assert "messages_history" in call_args[1]
        assert call_args[1]["temperature"] is None

        # Verify history was updated after the call
        assert len(task.message_history) == 1

        # Verify result
        assert isinstance(result, Step)
        assert not result.stop
        assert len(result.actions) == 2

    def test_step_only_appends_when_raw_output_exists(
        self, task, api_response_completed
    ):
        """Test that message_history only updates when raw_output is present."""
        task.task_description = "Test task"

        # Create response without raw_output
        response_without_raw = api_response_completed.copy()
        response_without_raw["raw_output"] = None
        response_obj = LLMResponse(**response_without_raw)
        task.client.create_message.return_value = response_obj

        task.step(b"screenshot")

        # History should not be updated when raw_output is None
        assert len(task.message_history) == 0


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

        task.step(b"screenshot_data")

        # Verify temperature is None (worker will use its default)
        call_args = task.client.create_message.call_args
        assert call_args[1]["temperature"] is None
