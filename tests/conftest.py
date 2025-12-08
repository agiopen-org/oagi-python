# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import os
from unittest.mock import Mock, patch

import httpx
import pytest

from oagi.types import Action, ActionType, Step
from oagi.types.models import Usage


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before and after each test."""
    env_vars = ["OAGI_LOG", "OAGI_BASE_URL", "OAGI_API_KEY"]

    # Store original values
    original_values = {}
    for var in env_vars:
        if var in os.environ:
            original_values[var] = os.environ[var]
            # Clear the environment variable for test isolation
            del os.environ[var]

    yield

    # Restore original values or remove if they didn't exist
    for var in env_vars:
        if var in original_values:
            os.environ[var] = original_values[var]
        elif var in os.environ:
            del os.environ[var]


@pytest.fixture
def api_env():
    """Set up API environment variables."""
    os.environ["OAGI_BASE_URL"] = "https://api.example.com"
    os.environ["OAGI_API_KEY"] = "test-key"
    return {
        "base_url": "https://api.example.com",
        "api_key": "test-key",
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.Client instance with patching."""
    with patch("oagi.client.sync.httpx.Client") as mock_class:
        mock_client = Mock()
        mock_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_httpx_client_class(mock_httpx_client):
    """Mock httpx.Client class - returns the already patched class."""
    # Since mock_httpx_client already patches the class, we just need to return the mock
    with patch("oagi.client.sync.httpx.Client") as mock_class:
        mock_class.return_value = mock_httpx_client
        yield mock_class


@pytest.fixture
def sample_action():
    """Sample Action object for testing."""
    return Action(type=ActionType.CLICK, argument="300, 150", count=1)


@pytest.fixture
def sample_usage():
    """Sample usage data."""
    return {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    }


@pytest.fixture
def sample_usage_obj(sample_usage):
    """Sample Usage object."""
    return Usage(**sample_usage)


@pytest.fixture
def upload_file_response():
    """Sample UploadFileResponse for S3 upload."""
    return {
        "url": "https://s3.amazonaws.com/presigned-url",
        "uuid": "test-uuid-123",
        "expires_at": 1677652888,
        "file_expires_at": 1677739288,
        "download_url": "https://cdn.example.com/test-uuid-123",
    }


@pytest.fixture
def mock_upload_response(upload_file_response):
    """Mock HTTP response for S3 presigned URL request."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = upload_file_response
    return mock_response


@pytest.fixture
def mock_s3_upload_response():
    """Mock HTTP response for S3 upload."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def sample_raw_output():
    """Sample raw output from the model."""
    return "<|think_start|>Need to click the button at coordinates 300, 150<|think_end|>\n<|action_start|>click(300, 150)<|action_end|>"


@pytest.fixture
def sample_raw_output_completed():
    """Sample raw output for completed task."""
    return "<|think_start|>The task has been completed successfully<|think_end|>\n<|action_start|>finish()<|action_end|>"


@pytest.fixture
def sample_step(sample_action):
    """Sample Step object for testing."""
    return Step(
        reason="Need to click the button at coordinates 300, 150",
        actions=[sample_action],
        stop=False,
    )


@pytest.fixture
def completed_step():
    """Sample completed Step object for testing."""
    return Step(
        reason="The task has been completed successfully",
        actions=[Action(type=ActionType.FINISH, argument="", count=1)],
        stop=True,
    )


@pytest.fixture
def mock_error_response():
    """Mock error HTTP response."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error": {
            "code": "authentication_error",
            "message": "Invalid API key",
        }
    }
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "API Error 401: authentication_error - Invalid API key",
        request=Mock(),
        response=mock_response,
    )
    return mock_response


@pytest.fixture
def mock_server_error():
    """Mock server error response."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    return mock_response


@pytest.fixture
def http_timeout_error():
    """Create an HTTP timeout exception."""
    return httpx.TimeoutException("Request timed out after 60 seconds")


@pytest.fixture
def http_status_error(mock_server_error):
    """Create an HTTP status error."""
    return httpx.HTTPStatusError(
        "Server error",
        request=Mock(),
        response=mock_server_error,
    )


@pytest.fixture
def mock_sync_client():
    """Create a mock SyncClient for task tests."""
    with patch("oagi.task.sync.SyncClient") as MockClient:
        mock_instance = Mock()
        mock_instance.api_key = "test-key"
        mock_instance.base_url = "https://test.example.com"
        MockClient.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_image():
    """Create a mock Image object (not URL)."""
    mock = Mock(spec=["read"])  # Only has read() method
    mock.read.return_value = b"fake image bytes"
    return mock


class MockImage:
    """Mock image class for testing."""

    def read(self) -> bytes:
        return b"mock screenshot data"


@pytest.fixture
def mock_image_class():
    """Create a MockImage instance for testing."""
    return MockImage()


@pytest.fixture
def mock_openai_response(sample_raw_output, sample_usage):
    """Create a mock OpenAI chat completion response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = sample_raw_output
    mock_response.usage = Mock(
        prompt_tokens=sample_usage["prompt_tokens"],
        completion_tokens=sample_usage["completion_tokens"],
        total_tokens=sample_usage["total_tokens"],
    )
    return mock_response


@pytest.fixture
def mock_openai_response_completed(sample_raw_output_completed, sample_usage):
    """Create a mock OpenAI chat completion response for completed task."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = sample_raw_output_completed
    mock_response.usage = Mock(
        prompt_tokens=sample_usage["prompt_tokens"],
        completion_tokens=sample_usage["completion_tokens"],
        total_tokens=sample_usage["total_tokens"],
    )
    return mock_response
