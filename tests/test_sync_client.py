# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import base64
import logging
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
def test_client(api_env):
    client = SyncClient(base_url=api_env["base_url"], api_key=api_env["api_key"])
    yield client
    client.close()


@pytest.fixture
def create_client():
    """Helper fixture to create and cleanup clients in tests."""
    clients = []

    def _create_client(*args, **kwargs):
        client = SyncClient(*args, **kwargs)
        clients.append(client)
        return client

    yield _create_client

    for client in clients:
        client.close()


class TestSyncClient:
    @pytest.mark.parametrize(
        "env_vars,init_params,expected_base_url,expected_api_key",
        [
            # Test with parameters only
            (
                {},
                {"base_url": "https://api.example.com", "api_key": "test-key"},
                "https://api.example.com",
                "test-key",
            ),
            # Test with environment variables only
            (
                {"OAGI_BASE_URL": "https://env.example.com", "OAGI_API_KEY": "env-key"},
                {},
                "https://env.example.com",
                "env-key",
            ),
            # Test parameters override environment variables
            (
                {"OAGI_BASE_URL": "https://env.example.com", "OAGI_API_KEY": "env-key"},
                {"base_url": "https://param.example.com", "api_key": "param-key"},
                "https://param.example.com",
                "param-key",
            ),
        ],
    )
    def test_init_configuration_sources(
        self, env_vars, init_params, expected_base_url, expected_api_key, create_client
    ):
        for key, value in env_vars.items():
            os.environ[key] = value

        client = create_client(**init_params)
        assert client.base_url == expected_base_url
        assert client.api_key == expected_api_key

    @pytest.mark.parametrize(
        "missing_param,provided_param,error_message",
        [
            ("base_url", {"api_key": "test-key"}, "OAGI base URL must be provided"),
            (
                "api_key",
                {"base_url": "https://api.example.com"},
                "OAGI API key must be provided",
            ),
            (
                "both",
                {},
                "OAGI base URL must be provided",
            ),  # base_url error comes first
        ],
    )
    def test_init_missing_configuration_raises_error(
        self, missing_param, provided_param, error_message
    ):
        with pytest.raises(ConfigurationError, match=error_message):
            SyncClient(**provided_param)

    def test_base_url_trailing_slash_stripped(self, create_client):
        client = create_client(base_url="https://api.example.com/", api_key="test-key")
        assert client.base_url == "https://api.example.com"

    def test_context_manager_support(self):
        with SyncClient(
            base_url="https://api.example.com", api_key="test-key"
        ) as client:
            assert client.base_url == "https://api.example.com"

    def test_create_message_success_with_basic_parameters(
        self, mock_httpx_client, mock_success_response, test_client
    ):
        mock_httpx_client.post.return_value = mock_success_response

        response = test_client.create_message(
            model="vision-model-v1",
            screenshot="iVBORw0KGgo...",
            task_description="Test task",
        )

        self._assert_successful_llm_response(response)
        self._assert_api_call_made(
            mock_httpx_client,
            {
                "model": "vision-model-v1",
                "screenshot": "iVBORw0KGgo...",
                "task_description": "Test task",
                "max_actions": 5,
            },
        )

    def test_create_message_with_all_optional_parameters(
        self, mock_httpx_client, test_client, api_response_completed
    ):
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

        expected_headers = {"x-api-key": "test-key", "x-api-version": "v1.2"}
        self._assert_api_call_made(
            mock_httpx_client,
            {
                "model": "vision-model-v1",
                "screenshot": "screenshot_data",
                "task_description": "Test task",
                "task_id": "existing-task",
                "instruction": "Click submit button",
                "max_actions": 10,
            },
            expected_headers,
        )

    @pytest.mark.parametrize(
        "error_setup,expected_exception,error_message",
        [
            # Authentication error from API response
            ("api_error", AuthenticationError, "Invalid API key"),
            # Non-JSON response error
            ("non_json_error", APIError, "Invalid response format"),
            # Timeout error
            ("timeout_error", RequestTimeoutError, "Request timed out"),
        ],
    )
    def test_create_message_error_scenarios(
        self,
        mock_httpx_client,
        test_client,
        error_setup,
        expected_exception,
        error_message,
    ):
        if error_setup == "api_error":
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "error": {"code": "authentication_error", "message": "Invalid API key"}
            }
            mock_httpx_client.post.return_value = mock_response
        elif error_setup == "non_json_error":
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.json.side_effect = ValueError("Not JSON")
            mock_httpx_client.post.return_value = mock_response
        elif error_setup == "timeout_error":
            mock_httpx_client.post.side_effect = httpx.TimeoutException(
                "Request timed out"
            )

        with pytest.raises(expected_exception, match=error_message):
            test_client.create_message(
                model="vision-model-v1",
                screenshot="test_screenshot",
                task_description="Test task"
                if error_setup == "timeout_error"
                else None,
            )

    def test_health_check_success(self, mock_httpx_client, test_client):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_httpx_client.get.return_value = mock_response

        result = test_client.health_check()

        assert result == {"status": "healthy"}
        mock_httpx_client.get.assert_called_once_with("/health")
        mock_response.raise_for_status.assert_called_once()

    def test_health_check_service_unavailable_error(
        self, mock_httpx_client, test_client
    ):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503 Service Unavailable", request=Mock(), response=mock_response
        )
        mock_httpx_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError, match="503 Service Unavailable"):
            test_client.health_check()

    def _assert_successful_llm_response(self, response):
        """Helper method to verify successful LLM response structure."""
        assert isinstance(response, LLMResponse)
        assert response.id == "test-123"
        assert response.task_id == "task-456"
        assert response.model == "vision-model-v1"
        assert response.task_description == "Test task"
        assert response.current_step == 1
        assert not response.is_complete
        assert len(response.actions) == 1
        assert response.actions[0].type == ActionType.CLICK
        assert response.actions[0].argument == "300, 150"  # Match conftest.py fixture
        assert response.usage.total_tokens == 150

    def _assert_api_call_made(self, mock_client, expected_json, expected_headers=None):
        """Helper method to verify API call was made correctly."""
        if expected_headers is None:
            expected_headers = {"x-api-key": "test-key"}

        mock_client.post.assert_called_once_with(
            "/v1/message",
            json=expected_json,
            headers=expected_headers,
            timeout=60,
        )


class TestHelperFunctions:
    @pytest.fixture
    def test_image_bytes(self):
        return b"test image data"

    @pytest.fixture
    def expected_base64(self, test_image_bytes):
        return base64.b64encode(test_image_bytes).decode("utf-8")

    def test_encode_screenshot_from_bytes(self, test_image_bytes, expected_base64):
        result = encode_screenshot_from_bytes(test_image_bytes)
        assert result == expected_base64

    @patch("builtins.open")
    def test_encode_screenshot_from_file_reads_correctly(
        self, mock_open, test_image_bytes, expected_base64
    ):
        mock_file = Mock()
        mock_file.read.return_value = test_image_bytes
        mock_open.return_value.__enter__.return_value = mock_file

        result = encode_screenshot_from_file("/path/to/image.png")

        assert result == expected_base64
        mock_open.assert_called_once_with("/path/to/image.png", "rb")


class TestTraceLogging:
    @pytest.mark.parametrize(
        "trace_headers,expected_logs",
        [
            # Response with trace headers
            (
                {"x-request-id": "req-123", "x-trace-id": "trace-456"},
                ["Request Id: req-123", "Trace Id: trace-456"],
            ),
            # Response with empty headers
            ({}, ["Request Id: ", "Trace Id: "]),
        ],
    )
    def test_trace_logging_with_http_error_response(
        self, mock_httpx_client, test_client, caplog, trace_headers, expected_logs
    ):
        mock_response = Mock()
        mock_response.headers = trace_headers

        error = httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        )
        error.response = mock_response
        mock_httpx_client.post.side_effect = error

        with caplog.at_level(logging.ERROR, logger="oagi.sync_client"):
            with pytest.raises(httpx.HTTPStatusError):
                test_client.create_message(
                    model="test-model", screenshot="test-screenshot"
                )

        for expected_log in expected_logs:
            assert expected_log in caplog.text

    def test_trace_logging_without_response_attribute(
        self, mock_httpx_client, test_client, caplog
    ):
        error = ValueError("Some error")
        mock_httpx_client.post.side_effect = error

        with caplog.at_level(logging.ERROR, logger="oagi.sync_client"):
            with pytest.raises(ValueError):
                test_client.create_message(
                    model="test-model", screenshot="test-screenshot"
                )

        assert "Request Id:" not in caplog.text
        assert "Trace Id:" not in caplog.text


class TestDataModels:
    def test_usage_model_properties(self):
        usage = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    @pytest.mark.parametrize(
        "error_data,expected_code,expected_message",
        [
            (
                {"code": "test_error", "message": "Test message"},
                "test_error",
                "Test message",
            ),
            (None, None, None),
        ],
    )
    def test_error_response_model_scenarios(
        self, error_data, expected_code, expected_message
    ):
        if error_data is None:
            error_response = ErrorResponse(error=None)
            assert error_response.error is None
        else:
            error_detail = ErrorDetail(**error_data)
            error_response = ErrorResponse(error=error_detail)
            assert error_response.error.code == expected_code
            assert error_response.error.message == expected_message

    def test_llm_response_model_complete_structure(self):
        action = Action(type=ActionType.CLICK, argument="100, 200", count=1)
        usage = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        response = LLMResponse(
            id="test-123",
            task_id="task-456",
            created=1677652288,
            model="vision-model-v1",
            task_description="Test task",
            current_step=1,
            is_complete=False,
            actions=[action],
            usage=usage,
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
        assert response.error is None
