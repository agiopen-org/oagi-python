# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import Mock, patch

import pytest

from oagi.short_task import ShortTask


@pytest.fixture
def short_task(mock_sync_client):
    return ShortTask(api_key="test-key", base_url="https://test.example.com")


class TestShortTaskInit:
    def test_init_with_default_model(self, mock_sync_client):
        task = ShortTask(api_key="test-key", base_url="https://test.example.com")
        assert task.model == "vision-model-v1"

    def test_init_with_custom_model(self, mock_sync_client):
        task = ShortTask(
            api_key="test-key",
            base_url="https://test.example.com",
            model="custom-model",
        )
        assert task.model == "custom-model"


class TestShortTaskAutoMode:
    def test_auto_mode_success(
        self, short_task, sample_llm_response, completed_llm_response
    ):
        # Mock executor and image provider
        mock_executor = Mock()
        mock_image_provider = Mock()
        mock_image_provider.side_effect = [b"image1", b"image2", b"image3"]

        # Setup responses: 2 in-progress, then completed
        short_task.client.create_message.side_effect = [
            sample_llm_response,  # init_task
            sample_llm_response,  # step 1
            sample_llm_response,  # step 2
            completed_llm_response,  # step 3 - completed
        ]

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            result = short_task.auto_mode(
                "Test auto task",
                max_steps=5,
                executor=mock_executor,
                image_provider=mock_image_provider,
            )

            assert result is True
            assert (
                mock_executor.call_count == 3
            )  # Called for all 3 steps including the completed one
            assert mock_image_provider.call_count == 3  # Called for all 3 steps

    def test_auto_mode_max_steps_reached(self, short_task, sample_llm_response):
        mock_executor = Mock()
        mock_image_provider = Mock()
        mock_image_provider.return_value = b"image"

        # All responses are in-progress (never completes)
        short_task.client.create_message.return_value = sample_llm_response

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            result = short_task.auto_mode(
                "Test auto task",
                max_steps=3,
                executor=mock_executor,
                image_provider=mock_image_provider,
            )

            assert result is False
            assert mock_executor.call_count == 3
            assert mock_image_provider.call_count == 3

    def test_auto_mode_without_executor(
        self, short_task, sample_llm_response, completed_llm_response
    ):
        mock_image_provider = Mock()
        mock_image_provider.return_value = b"image"

        short_task.client.create_message.side_effect = [
            sample_llm_response,  # init_task
            completed_llm_response,  # step 1 - completed
        ]

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            result = short_task.auto_mode(
                "Test auto task",
                max_steps=5,
                executor=None,
                image_provider=mock_image_provider,
            )

            assert result is True
            assert mock_image_provider.call_count == 1

    def test_auto_mode_immediate_completion(
        self, short_task, sample_llm_response, completed_llm_response
    ):
        mock_executor = Mock()
        mock_image_provider = Mock()
        mock_image_provider.return_value = b"image"

        # First step after init returns completed
        short_task.client.create_message.side_effect = [
            sample_llm_response,  # init_task
            completed_llm_response,  # step 1 - immediately completed
        ]

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            result = short_task.auto_mode(
                "Test auto task",
                max_steps=10,
                executor=mock_executor,
                image_provider=mock_image_provider,
            )

            assert result is True
            assert (
                mock_executor.call_count == 1
            )  # Actions are executed even when task is complete
            assert mock_image_provider.call_count == 1

    def test_auto_mode_with_default_parameters(
        self, short_task, completed_llm_response
    ):
        # Mock image provider to prevent actual implementation
        mock_image_provider = Mock()
        mock_image_provider.return_value = b"image"

        short_task.client.create_message.side_effect = [
            completed_llm_response,  # init_task returns completed response
            completed_llm_response,  # step 1 - completed
        ]

        with patch("oagi.task.encode_screenshot_from_bytes") as mock_encode:
            mock_encode.return_value = "base64_encoded"

            # Should work with None executor
            result = short_task.auto_mode(
                "Test task",
                max_steps=1,
                executor=None,
                image_provider=mock_image_provider,
            )

            assert result is True
