# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import logging
import os
from unittest.mock import Mock, patch

import httpx
import pytest

from oagi.client import SyncClient
from oagi.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    RequestTimeoutError,
)
from oagi.types import Action, ActionType
from oagi.types.models import (
    ErrorDetail,
    ErrorResponse,
    LLMResponse,
    UploadFileResponse,
    Usage,
)


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
            (
                "api_key",
                {"base_url": "https://api.example.com"},
                "OAGI API key must be provided",
            ),
            (
                "both",
                {},
                "OAGI API key must be provided",
            ),
        ],
    )
    def test_init_missing_configuration_raises_error(
        self, missing_param, provided_param, error_message
    ):
        with pytest.raises(ConfigurationError, match=error_message):
            SyncClient(**provided_param)

    def test_init_default_base_url(self, create_client):
        """Test that base_url defaults to prod URL if not provided."""
        # Ensure OAGI_BASE_URL is not set
        if "OAGI_BASE_URL" in os.environ:
            del os.environ["OAGI_BASE_URL"]

        client = create_client(api_key="test-key")
        assert client.base_url == "https://api.agiopen.org"

    def test_base_url_trailing_slash_stripped(self, create_client):
        client = create_client(base_url="https://api.example.com/", api_key="test-key")
        assert client.base_url == "https://api.example.com"

    def test_context_manager_support(self):
        with SyncClient(
            base_url="https://api.example.com", api_key="test-key"
        ) as client:
            assert client.base_url == "https://api.example.com"

    def test_create_message_success_with_basic_parameters(
        self,
        mock_httpx_client,
        mock_success_response,
        test_client,
        mock_upload_response,
        mock_s3_upload_response,
        upload_file_response,
    ):
        # Mock S3 upload flow
        mock_httpx_client.get.return_value = mock_upload_response
        with patch.object(test_client, "upload_client") as mock_upload_client:
            mock_upload_client.put.return_value = mock_s3_upload_response
            mock_httpx_client.post.return_value = mock_success_response

            response = test_client.create_message(
                model="vision-model-v1",
                screenshot=b"iVBORw0KGgo...",
                task_description="Test task",
            )

            self._assert_successful_llm_response(response)
            # Verify S3 presigned URL was requested
            mock_httpx_client.get.assert_called_once()
            # Verify upload to S3 happened
            mock_upload_client.put.assert_called_once_with(
                url=upload_file_response["url"], content=b"iVBORw0KGgo..."
            )
            # Verify /v2/message endpoint was called with OpenAI format
            self._assert_v2_api_call_made(
                mock_httpx_client,
                {
                    "model": "vision-model-v1",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": upload_file_response["download_url"]
                                    },
                                }
                            ],
                        }
                    ],
                    "task_description": "Test task",
                },
            )

    def test_create_message_with_all_optional_parameters(
        self,
        mock_httpx_client,
        test_client,
        api_response_completed,
        mock_upload_response,
        mock_s3_upload_response,
        upload_file_response,
    ):
        completed_response = Mock()
        completed_response.status_code = 200
        completed_response.json.return_value = api_response_completed

        # Mock S3 upload flow
        mock_httpx_client.get.return_value = mock_upload_response
        with patch.object(test_client, "upload_client") as mock_upload_client:
            mock_upload_client.put.return_value = mock_s3_upload_response
            mock_httpx_client.post.return_value = completed_response

            test_client.create_message(
                model="vision-model-v1",
                screenshot=b"screenshot_data",
                task_description="Test task",
                task_id="existing-task",
                instruction="Click submit button",
                messages_history=[],
                api_version="v1.2",
            )

            expected_headers = {"x-api-key": "test-key", "x-api-version": "v1.2"}
            self._assert_v2_api_call_made(
                mock_httpx_client,
                {
                    "model": "vision-model-v1",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": upload_file_response["download_url"]
                                    },
                                },
                                {"type": "text", "text": "Click submit button"},
                            ],
                        }
                    ],
                    "task_description": "Test task",
                    "task_id": "existing-task",
                },
                expected_headers,
            )

    def test_create_message_with_temperature(
        self,
        mock_httpx_client,
        test_client,
        mock_success_response,
        mock_upload_response,
        mock_s3_upload_response,
        upload_file_response,
    ):
        # Mock S3 upload flow
        mock_httpx_client.get.return_value = mock_upload_response
        with patch.object(test_client, "upload_client") as mock_upload_client:
            mock_upload_client.put.return_value = mock_s3_upload_response
            mock_httpx_client.post.return_value = mock_success_response

            test_client.create_message(
                model="vision-model-v1",
                screenshot=b"screenshot_data",
                task_description="Test task",
                temperature=0.7,
            )

            self._assert_v2_api_call_made(
                mock_httpx_client,
                {
                    "model": "vision-model-v1",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": upload_file_response["download_url"]
                                    },
                                }
                            ],
                        }
                    ],
                    "task_description": "Test task",
                    "temperature": 0.7,
                },
            )

    @pytest.mark.parametrize(
        "error_setup,expected_exception,error_message",
        [
            # Authentication error from API response
            ("api_error", AuthenticationError, "Invalid API key"),
            # Non-JSON response error
            ("non_json_error", APIError, "Invalid response format"),
            # Timeout error during /v2/message call
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
        mock_upload_response,
        mock_s3_upload_response,
    ):
        # Mock S3 upload flow (succeeds in all cases)
        mock_httpx_client.get.return_value = mock_upload_response

        with patch.object(test_client, "upload_client") as mock_upload_client:
            mock_upload_client.put.return_value = mock_s3_upload_response

            if error_setup == "api_error":
                mock_response = Mock()
                mock_response.status_code = 401
                mock_response.json.return_value = {
                    "error": {
                        "code": "authentication_error",
                        "message": "Invalid API key",
                    }
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
                    screenshot=b"test_screenshot",
                    task_description="Test task",
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

    def test_get_s3_presigned_url_success(
        self, mock_httpx_client, test_client, mock_upload_response, upload_file_response
    ):
        mock_httpx_client.get.return_value = mock_upload_response

        result = test_client.get_s3_presigned_url(api_version="v1.2")

        assert isinstance(result, UploadFileResponse)
        assert result.url == upload_file_response["url"]
        assert result.uuid == upload_file_response["uuid"]
        mock_httpx_client.get.assert_called_once_with(
            "/v1/file/upload",
            headers={"x-api-key": "test-key", "x-api-version": "v1.2"},
            timeout=60,
        )

    def test_upload_to_s3_success(self, test_client, mock_s3_upload_response):
        with patch.object(test_client, "upload_client") as mock_upload_client:
            mock_upload_client.put.return_value = mock_s3_upload_response

            test_client.upload_to_s3(
                url="https://s3.amazonaws.com/test", content=b"test content"
            )

            mock_upload_client.put.assert_called_once_with(
                url="https://s3.amazonaws.com/test", content=b"test content"
            )
            mock_s3_upload_response.raise_for_status.assert_called_once()

    def test_put_s3_presigned_url_success(
        self,
        mock_httpx_client,
        test_client,
        mock_upload_response,
        mock_s3_upload_response,
        upload_file_response,
    ):
        mock_httpx_client.get.return_value = mock_upload_response
        with patch.object(test_client, "upload_client") as mock_upload_client:
            mock_upload_client.put.return_value = mock_s3_upload_response

            result = test_client.put_s3_presigned_url(
                screenshot=b"test screenshot", api_version="v1.2"
            )

            assert isinstance(result, UploadFileResponse)
            assert result.url == upload_file_response["url"]
            # Verify it called get presigned URL
            mock_httpx_client.get.assert_called_once()
            # Verify it uploaded to S3
            mock_upload_client.put.assert_called_once_with(
                url=upload_file_response["url"], content=b"test screenshot"
            )

    def _assert_successful_llm_response(self, response):
        """Helper method to verify successful LLM response structure."""
        assert isinstance(response, LLMResponse)
        assert response.id == "test-123"
        assert response.task_id == "task-456"
        assert response.model == "lux-actor-1"
        assert response.task_description == "Test task"
        assert not response.is_complete
        assert len(response.actions) == 1
        assert response.actions[0].type == ActionType.CLICK
        assert response.actions[0].argument == "300, 150"  # Match conftest.py fixture
        assert response.usage.total_tokens == 150

    def _assert_api_call_made(self, mock_client, expected_json, expected_headers=None):
        """Helper method to verify API call was made correctly (V1 API)."""
        if expected_headers is None:
            expected_headers = {"x-api-key": "test-key"}

        mock_client.post.assert_called_once_with(
            "/v1/message",
            json=expected_json,
            headers=expected_headers,
            timeout=60,
        )

    def _assert_v2_api_call_made(
        self, mock_client, expected_json, expected_headers=None
    ):
        """Helper method to verify V2 API call was made correctly."""
        if expected_headers is None:
            expected_headers = {"x-api-key": "test-key"}

        mock_client.post.assert_called_once_with(
            "/v2/message",
            json=expected_json,
            headers=expected_headers,
            timeout=60,
        )


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
        self,
        mock_httpx_client,
        test_client,
        caplog,
        trace_headers,
        expected_logs,
        mock_upload_response,
        mock_s3_upload_response,
    ):
        # Mock S3 upload flow (succeeds)
        mock_httpx_client.get.return_value = mock_upload_response
        with patch.object(test_client, "upload_client") as mock_upload_client:
            mock_upload_client.put.return_value = mock_s3_upload_response

            # /v2/message returns error
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
                        model="test-model", screenshot=b"test-screenshot"
                    )

            for expected_log in expected_logs:
                assert expected_log in caplog.text

    def test_trace_logging_without_response_attribute(
        self,
        mock_httpx_client,
        test_client,
        caplog,
        mock_upload_response,
        mock_s3_upload_response,
    ):
        # Mock S3 upload flow (succeeds)
        mock_httpx_client.get.return_value = mock_upload_response
        with patch.object(test_client, "upload_client") as mock_upload_client:
            mock_upload_client.put.return_value = mock_s3_upload_response

            # /v2/message raises ValueError (no response attribute)
            error = ValueError("Some error")
            mock_httpx_client.post.side_effect = error

            with caplog.at_level(logging.ERROR, logger="oagi.sync_client"):
                with pytest.raises(ValueError):
                    test_client.create_message(
                        model="test-model", screenshot=b"test-screenshot"
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
            model="lux-actor-1",
            task_description="Test task",
            is_complete=False,
            actions=[action],
            usage=usage,
        )

        assert response.id == "test-123"
        assert response.task_id == "task-456"
        assert response.object == "task.completion"  # default value
        assert response.created == 1677652288
        assert response.model == "lux-actor-1"
        assert response.task_description == "Test task"
        assert not response.is_complete
        assert len(response.actions) == 1
        assert response.actions[0].type == ActionType.CLICK
        assert response.usage.total_tokens == 150
        assert response.error is None
