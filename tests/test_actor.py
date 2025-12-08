# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import patch

import pytest

from oagi.constants import MODEL_ACTOR
from oagi.task import Actor
from oagi.types import ActionType, Step
from oagi.types.models import UploadFileResponse


@pytest.fixture
def actor(mock_sync_client):
    """Create an Actor instance with mocked client."""
    return Actor(api_key="test-key", base_url="https://test.example.com")


@pytest.fixture
def mock_upload_file_response():
    """Mock UploadFileResponse for S3 upload."""
    return UploadFileResponse(
        url="https://s3.amazonaws.com/presigned-url",
        uuid="test-uuid-123",
        expires_at=1677652888,
        file_expires_at=1677739288,
        download_url="https://cdn.example.com/test-uuid-123",
    )


class TestActorInit:
    def test_init_with_parameters(self, mock_sync_client):
        actor = Actor(api_key="test-key", base_url="https://test.example.com")
        assert actor.api_key == "test-key"
        assert actor.base_url == "https://test.example.com"
        assert actor.task_id is not None
        assert isinstance(actor.task_id, str)
        assert len(actor.task_id) == 32  # UUID hex without dashes
        assert actor.task_description is None
        assert actor.model == MODEL_ACTOR
        assert actor.message_history == []

    def test_init_with_custom_model(self, mock_sync_client):
        actor = Actor(
            api_key="test-key",
            base_url="https://test.example.com",
            model="custom-model",
        )
        assert actor.model == "custom-model"

    def test_init_with_env_vars(self, mock_sync_client):
        with patch.dict(
            "os.environ",
            {"OAGI_BASE_URL": "https://env.example.com", "OAGI_API_KEY": "env-key"},
        ):
            mock_sync_client.api_key = "env-key"
            mock_sync_client.base_url = "https://env.example.com"
            actor = Actor()
            assert actor.api_key == "env-key"
            assert actor.base_url == "https://env.example.com"

    def test_init_parameters_override_env_vars(self, mock_sync_client):
        with patch.dict(
            "os.environ",
            {"OAGI_BASE_URL": "https://env.example.com", "OAGI_API_KEY": "env-key"},
        ):
            actor = Actor(
                api_key="override-key", base_url="https://override.example.com"
            )
            assert actor.api_key == "test-key"  # From mock_sync_client
            assert actor.base_url == "https://test.example.com"  # From mock_sync_client


class TestActorInitTask:
    def test_init_task_success(self, actor):
        original_task_id = actor.task_id

        actor.init_task("Test task description", max_steps=10)

        assert actor.task_description == "Test task description"
        # task_id is regenerated on init_task to create a fresh task
        assert actor.task_id != original_task_id
        assert isinstance(actor.task_id, str)
        assert len(actor.task_id) == 32  # UUID hex without dashes


class TestActorStep:
    def test_step_with_image_object(
        self,
        actor,
        mock_image,
        sample_step,
        sample_usage_obj,
        mock_upload_file_response,
    ):
        actor.task_description = "Test task"
        actor.task_id = "existing-task"

        # Setup mocks
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )

        result = actor.step(mock_image)

        # Verify Image.read() was called
        mock_image.read.assert_called_once()

        # Verify S3 upload was called
        actor.client.put_s3_presigned_url.assert_called_once()

        # Verify chat_completion was called with messages
        actor.client.chat_completion.assert_called_once()
        call_args = actor.client.chat_completion.call_args
        assert call_args[1]["model"] == MODEL_ACTOR
        assert "messages" in call_args[1]
        assert call_args[1]["temperature"] is None

        # Verify returned Step
        assert isinstance(result, Step)
        assert result.stop is False

        # Verify message_history was updated (user + assistant)
        assert len(actor.message_history) == 2
        assert actor.message_history[0]["role"] == "user"
        assert actor.message_history[1]["role"] == "assistant"

    def test_step_with_bytes_directly(
        self, actor, sample_step, sample_usage_obj, mock_upload_file_response
    ):
        actor.task_description = "Test task"
        original_task_id = actor.task_id

        # Setup mocks
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )

        image_bytes = b"raw image bytes"
        result = actor.step(image_bytes)

        # Verify S3 upload was called
        actor.client.put_s3_presigned_url.assert_called_once_with(image_bytes)

        # Verify chat_completion was called with messages
        call_args = actor.client.chat_completion.call_args
        assert call_args[1]["model"] == MODEL_ACTOR
        assert "messages" in call_args[1]
        assert call_args[1]["temperature"] is None

        # task_id doesn't change
        assert actor.task_id == original_task_id

        # Verify returned Step
        assert isinstance(result, Step)
        assert result.stop is False

    def test_step_with_url_directly(self, actor, sample_step, sample_usage_obj):
        """Test that step with URL skips S3 upload."""
        actor.task_description = "Test task"

        # Setup mocks
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )

        screenshot_url = "https://cdn.example.com/screenshot.png"
        result = actor.step(screenshot_url)

        # Verify S3 upload was NOT called (URL used directly)
        actor.client.put_s3_presigned_url.assert_not_called()

        # Verify chat_completion was called with messages containing the URL
        actor.client.chat_completion.assert_called_once()
        # After step: message_history has 2 (user + assistant)
        assert len(actor.message_history) == 2
        assert screenshot_url in str(actor.message_history[0])  # URL in user message

        assert isinstance(result, Step)

    def test_step_without_init_task_raises_error(self, actor):
        with pytest.raises(
            ValueError, match="Task description must be set. Call init_task\\(\\) first"
        ):
            actor.step(b"image bytes")

    def test_step_with_completed_response(
        self, actor, completed_step, sample_usage_obj, mock_upload_file_response
    ):
        actor.task_description = "Test task"
        actor.task_id = "task-456"

        # Setup mocks
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response
        actor.client.chat_completion.return_value = (
            completed_step,
            "<|think_start|>done<|think_end|>\n<|action_start|>finish()<|action_end|>",
            sample_usage_obj,
        )

        result = actor.step(b"image bytes")

        assert result.stop is True
        assert result.reason == "The task has been completed successfully"
        assert len(result.actions) == 1
        assert result.actions[0].type == ActionType.FINISH

    def test_step_handles_exception(self, actor, mock_upload_file_response):
        actor.task_description = "Test task"
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response
        actor.client.chat_completion.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            actor.step(b"image bytes")

    def test_step_raises_error_when_max_steps_reached(
        self, actor, sample_step, sample_usage_obj, mock_upload_file_response
    ):
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )
        actor.init_task("Test task", max_steps=3)

        # Execute 3 steps successfully
        for _ in range(3):
            actor.step(b"image bytes")

        # 4th step should raise error
        with pytest.raises(ValueError, match="Max steps limit \\(3\\) reached"):
            actor.step(b"image bytes")

    def test_step_with_instruction(
        self, actor, sample_step, sample_usage_obj, mock_upload_file_response
    ):
        """Test that instruction parameter is accepted (though currently unused)."""
        actor.task_description = "Test task"
        actor.task_id = "existing-task"

        # Setup mocks
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )

        result = actor.step(b"image bytes", instruction="Click the submit button")

        # Verify chat_completion was called
        actor.client.chat_completion.assert_called_once()
        assert isinstance(result, Step)
        assert not result.stop


class TestActorContextManager:
    def test_context_manager(self, mock_sync_client):
        with Actor(api_key="test-key", base_url="https://test.example.com") as actor:
            assert actor.api_key == "test-key"
            assert actor.base_url == "https://test.example.com"

        # Verify close was called
        mock_sync_client.close.assert_called_once()

    def test_close_method(self, actor):
        actor.close()
        actor.client.close.assert_called_once()

    def test_context_manager_with_exception(self, mock_sync_client):
        try:
            with Actor(api_key="test-key", base_url="https://test.example.com"):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify close was still called despite exception
        mock_sync_client.close.assert_called_once()


class TestActorIntegrationScenarios:
    def test_full_workflow(
        self,
        actor,
        sample_step,
        completed_step,
        sample_usage_obj,
        mock_upload_file_response,
    ):
        """Test a complete workflow from init to completion."""
        # Initialize task
        actor.init_task("Complete workflow test")
        task_id_after_init = actor.task_id

        assert actor.task_description == "Complete workflow test"

        # Setup mocks
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response

        # First step - in progress
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )
        step1 = actor.step(b"screenshot1")
        assert not step1.stop
        assert len(step1.actions) == 1
        # task_id stays the same across steps
        assert actor.task_id == task_id_after_init

        # Second step - completed
        actor.client.chat_completion.return_value = (
            completed_step,
            "<|think_start|>done<|think_end|>\n<|action_start|>finish()<|action_end|>",
            sample_usage_obj,
        )
        step2 = actor.step(b"screenshot2")
        assert step2.stop
        assert len(step2.actions) == 1
        assert actor.task_id == task_id_after_init


class TestActorHistory:
    """Test Actor class message history functionality."""

    def test_init_task_initializes_empty_history(self, actor):
        """Test that init_task starts with empty message history."""
        actor.init_task("Test task", max_steps=5)

        assert actor.message_history == []
        assert actor.task_description == "Test task"

    def test_step_updates_message_history(
        self, actor, sample_step, sample_usage_obj, mock_upload_file_response
    ):
        """Test that step updates message_history with user and assistant messages."""
        actor.task_description = "Test task"
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )

        # First step
        actor.step(b"screenshot1")

        # Verify message_history was updated with user + assistant messages
        assert len(actor.message_history) == 2
        assert actor.message_history[0]["role"] == "user"
        assert actor.message_history[1]["role"] == "assistant"
        assert "content" in actor.message_history[0]
        assert "content" in actor.message_history[1]

    def test_step_accumulates_history_across_steps(
        self, actor, sample_step, sample_usage_obj, mock_upload_file_response
    ):
        """Test that message_history accumulates across multiple steps."""
        actor.task_description = "Test task"
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )

        # First step adds user + assistant messages
        actor.step(b"screenshot1")
        assert len(actor.message_history) == 2

        # Second step adds another user + assistant
        actor.step(b"screenshot2")
        assert len(actor.message_history) == 4

        # Should alternate user/assistant
        assert actor.message_history[0]["role"] == "user"
        assert actor.message_history[1]["role"] == "assistant"
        assert actor.message_history[2]["role"] == "user"
        assert actor.message_history[3]["role"] == "assistant"

    def test_step_only_appends_assistant_when_raw_output_exists(
        self, actor, sample_step, sample_usage_obj, mock_upload_file_response
    ):
        """Test that assistant message only added when raw_output is present."""
        actor.task_description = "Test task"
        actor.client.put_s3_presigned_url.return_value = mock_upload_file_response

        # Return empty raw_output
        actor.client.chat_completion.return_value = (sample_step, "", sample_usage_obj)

        actor.step(b"screenshot")

        # User message is always added, but assistant message skipped when empty
        assert len(actor.message_history) == 1
        assert actor.message_history[0]["role"] == "user"


class TestActorTemperature:
    def test_task_with_default_temperature(
        self, mock_sync_client, sample_step, sample_usage_obj
    ):
        """Test that actor uses default temperature when provided."""
        mock_upload_response = UploadFileResponse(
            url="https://s3.amazonaws.com/presigned-url",
            uuid="test-uuid-123",
            expires_at=1677652888,
            file_expires_at=1677739288,
            download_url="https://cdn.example.com/test-uuid-123",
        )

        actor = Actor(
            api_key="test-key",
            base_url="https://test.example.com",
            temperature=0.5,
        )
        actor.task_description = "Test task"
        actor.client.put_s3_presigned_url.return_value = mock_upload_response
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )

        actor.step(b"screenshot_data")

        # Verify temperature is passed to chat_completion
        call_args = actor.client.chat_completion.call_args
        assert call_args[1]["temperature"] == 0.5

    def test_step_temperature_overrides_task_default(
        self, mock_sync_client, sample_step, sample_usage_obj
    ):
        """Test that step temperature overrides actor default."""
        mock_upload_response = UploadFileResponse(
            url="https://s3.amazonaws.com/presigned-url",
            uuid="test-uuid-123",
            expires_at=1677652888,
            file_expires_at=1677739288,
            download_url="https://cdn.example.com/test-uuid-123",
        )

        actor = Actor(
            api_key="test-key",
            base_url="https://test.example.com",
            temperature=0.5,
        )
        actor.task_description = "Test task"
        actor.client.put_s3_presigned_url.return_value = mock_upload_response
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )

        # Call step with different temperature
        actor.step(b"screenshot_data", temperature=0.9)

        # Verify step temperature (0.9) is used, not actor default (0.5)
        call_args = actor.client.chat_completion.call_args
        assert call_args[1]["temperature"] == 0.9

    def test_step_without_any_temperature(
        self, mock_sync_client, sample_step, sample_usage_obj
    ):
        """Test that when no temperature is provided, None is passed."""
        mock_upload_response = UploadFileResponse(
            url="https://s3.amazonaws.com/presigned-url",
            uuid="test-uuid-123",
            expires_at=1677652888,
            file_expires_at=1677739288,
            download_url="https://cdn.example.com/test-uuid-123",
        )

        actor = Actor(api_key="test-key", base_url="https://test.example.com")
        actor.task_description = "Test task"
        actor.client.put_s3_presigned_url.return_value = mock_upload_response
        actor.client.chat_completion.return_value = (
            sample_step,
            "<|think_start|>test<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>",
            sample_usage_obj,
        )

        actor.step(b"screenshot_data")

        # Verify temperature is None (model will use its default)
        call_args = actor.client.chat_completion.call_args
        assert call_args[1]["temperature"] is None
