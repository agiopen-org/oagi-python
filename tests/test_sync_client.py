# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import base64
import os
from unittest.mock import Mock, patch

import httpx
import pytest

from oagi.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    RequestTimeoutError,
)
from oagi.sync_client import (
    ErrorDetail,
    ErrorResponse,
    LLMResponse,
    SyncClient,
    Usage,
    encode_screenshot_from_bytes,
    encode_screenshot_from_file,
)
from oagi.types import Action, ActionType


@pytest.fixture
def mock_health_response():
    mock_response = Mock()
    mock_response.json.return_value = {"status": "healthy"}
    return mock_response


@pytest.fixture
def test_client(api_env):
    client = SyncClient(base_url=api_env["base_url"], api_key=api_env["api_key"])
    yield client
    client.close()


class TestSyncClient:
    def test_init_with_parameters(self):
        client = SyncClient(base_url="https://api.example.com", api_key="test-key")
        assert client.base_url == "https://api.example.com"
        assert client.api_key == "test-key"
        client.close()

    def test_init_with_env_vars(self):
        os.environ["OAGI_BASE_URL"] = "https://env.example.com"
        os.environ["OAGI_API_KEY"] = "env-key"

        client = SyncClient()
        assert client.base_url == "https://env.example.com"
        assert client.api_key == "env-key"
        client.close()

    def test_init_parameters_override_env_vars(self):
        os.environ["OAGI_BASE_URL"] = "https://env.example.com"
        os.environ["OAGI_API_KEY"] = "env-key"

        client = SyncClient(base_url="https://param.example.com", api_key="param-key")
        assert client.base_url == "https://param.example.com"
        assert client.api_key == "param-key"
        client.close()

    def test_init_missing_base_url_raises_error(self):
        with pytest.raises(ConfigurationError, match="OAGI base URL must be provided"):
            SyncClient(api_key="test-key")

    def test_init_missing_api_key_raises_error(self):
        with pytest.raises(ConfigurationError, match="OAGI API key must be provided"):
            SyncClient(base_url="https://api.example.com")

    def test_init_missing_both_raises_base_url_error_first(self):
        with pytest.raises(ConfigurationError, match="OAGI base URL must be provided"):
            SyncClient()

    def test_base_url_trailing_slash_stripped(self):
        client = SyncClient(base_url="https://api.example.com/", api_key="test-key")
        assert client.base_url == "https://api.example.com"
        client.close()

    def test_context_manager(self):
        with SyncClient(
            base_url="https://api.example.com", api_key="test-key"
        ) as client:
            assert client.base_url == "https://api.example.com"

    def test_create_message_success(
        self, mock_httpx_client, api_response_data, test_client
    ):
        # Create mock response with correct data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response_data
        mock_httpx_client.post.return_value = mock_response

        response = test_client.create_message(
            model="vision-model-v1",
            screenshot="iVBORw0KGgo...",
            task_description="Test task",
        )

        assert isinstance(response, LLMResponse)
        assert response.id == "test-123"
        assert response.task_id == "task-456"
        assert response.model == "vision-model-v1"
        assert response.task_description == "Test task"
        assert response.current_step == 1
        assert not response.is_complete
        assert len(response.actions) == 1
        assert response.actions[0].type == ActionType.CLICK
        assert response.actions[0].argument == "100, 200"
        assert response.usage.total_tokens == 150

        # Verify the API call
        mock_httpx_client.post.assert_called_once_with(
            "/v1/message",
            json={
                "model": "vision-model-v1",
                "screenshot": "iVBORw0KGgo...",
                "task_description": "Test task",
                "max_actions": 5,
            },
            headers={"x-api-key": "test-key"},
            timeout=60,
        )

    def test_create_message_with_all_parameters(
        self, mock_httpx_client, test_client, api_response_completed
    ):
        # Create a completed task response
        completed_response = Mock()
        completed_response.status_code = 200
        completed_response.json.return_value = api_response_completed
        mock_httpx_client.post.return_value = completed_response

        test_client.create_message(
            model="vision-model-v1",
            screenshot="screenshot_data",
            task_description="Test task",
            task_id="existing-task",
            instruction="Click submit button",
            max_actions=10,
            api_version="v1.2",
        )

        # Verify headers include api version
        expected_headers = {"x-api-key": "test-key", "x-api-version": "v1.2"}
        mock_httpx_client.post.assert_called_once_with(
            "/v1/message",
            json={
                "model": "vision-model-v1",
                "screenshot": "screenshot_data",
                "task_description": "Test task",
                "task_id": "existing-task",
                "instruction": "Click submit button",
                "max_actions": 10,
            },
            headers=expected_headers,
            timeout=60,
        )

    def test_create_message_error_response(
        self, mock_httpx_client, mock_error_response, test_client
    ):
        mock_httpx_client.post.return_value = mock_error_response

        with pytest.raises(
            AuthenticationError,
            match="Invalid API key",
        ):
            test_client.create_message(
                model="vision-model-v1", screenshot="test_screenshot"
            )

    def test_create_message_non_json_error_response(
        self, mock_httpx_client, test_client
    ):
        # Mock non-JSON error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_httpx_client.post.return_value = mock_response

        with pytest.raises(APIError, match="Invalid response format"):
            test_client.create_message(
                model="vision-model-v1", screenshot="test_screenshot"
            )

    def test_create_message_timeout(self, mock_httpx_client, test_client):
        # Mock a timeout error
        mock_httpx_client.post.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(RequestTimeoutError, match="Request timed out"):
            test_client.create_message(
                model="vision-model-v1",
                screenshot="test_screenshot",
                task_description="Test task",
            )

        # Verify the request was made with the correct timeout
        mock_httpx_client.post.assert_called_once_with(
            "/v1/message",
            json={
                "model": "vision-model-v1",
                "screenshot": "test_screenshot",
                "task_description": "Test task",
                "max_actions": 5,
            },
            headers={"x-api-key": "test-key"},
            timeout=60,
        )

    def test_health_check_success(
        self, mock_httpx_client, mock_health_response, test_client
    ):
        mock_httpx_client.get.return_value = mock_health_response

        result = test_client.health_check()

        assert result == {"status": "healthy"}
        mock_httpx_client.get.assert_called_once_with("/health")
        mock_health_response.raise_for_status.assert_called_once()

    def test_health_check_error(self, mock_httpx_client, test_client):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503 Service Unavailable", request=Mock(), response=mock_response
        )
        mock_httpx_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError, match="503 Service Unavailable"):
            test_client.health_check()


@pytest.fixture
def test_image_bytes():
    return b"test image data"


@pytest.fixture
def expected_base64(test_image_bytes):
    return base64.b64encode(test_image_bytes).decode("utf-8")


class TestHelperFunctions:
    def test_encode_screenshot_from_bytes(self, test_image_bytes, expected_base64):
        result = encode_screenshot_from_bytes(test_image_bytes)
        assert result == expected_base64

    @patch("builtins.open")
    def test_encode_screenshot_from_file(
        self, mock_open, test_image_bytes, expected_base64
    ):
        mock_file = Mock()
        mock_file.read.return_value = test_image_bytes
        mock_open.return_value.__enter__.return_value = mock_file

        result = encode_screenshot_from_file("/path/to/image.png")

        assert result == expected_base64
        mock_open.assert_called_once_with("/path/to/image.png", "rb")


@pytest.fixture
def sample_usage():
    return Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)


@pytest.fixture
def sample_action():
    return Action(type=ActionType.CLICK, argument="100, 200", count=1)


class TestDataModels:
    def test_usage_model(self, sample_usage):
        assert sample_usage.prompt_tokens == 100

        assert sample_usage.completion_tokens == 50
        assert sample_usage.total_tokens == 150

    def test_error_response_model(self):
        # Test with error detail
        error = ErrorResponse(
            error=ErrorDetail(code="test_error", message="Test message")
        )
        assert error.error.code == "test_error"
        assert error.error.message == "Test message"

        # Test with None error (successful response)
        error_none = ErrorResponse(error=None)
        assert error_none.error is None

    def test_llm_response_model(self, sample_action, sample_usage):
        response = LLMResponse(
            id="test-123",
            task_id="task-456",
            created=1677652288,
            model="vision-model-v1",
            task_description="Test task",
            current_step=1,
            is_complete=False,
            actions=[sample_action],
            usage=sample_usage,
        )

        assert response.id == "test-123"
        assert response.task_id == "task-456"
        assert response.object == "task.completion"  # default value
        assert response.created == 1677652288
        assert response.model == "vision-model-v1"
        assert response.task_description == "Test task"
        assert response.current_step == 1
        assert not response.is_complete
        assert len(response.actions) == 1
        assert response.actions[0].type == ActionType.CLICK
        assert response.usage.total_tokens == 150
        assert response.error is None  # No error in successful response
