# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import pytest_asyncio

from oagi.async_client import AsyncClient, LLMResponse
from oagi.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    RequestTimeoutError,
)
from oagi.types import ActionType


@pytest_asyncio.fixture
async def async_client(api_env):
    client = AsyncClient(base_url=api_env["base_url"], api_key=api_env["api_key"])
    yield client
    await client.close()


@pytest.fixture
def mock_response_data():
    return {
        "id": "test-id",
        "task_id": "task-123",
        "object": "task.completion",
        "created": 1234567890,
        "model": "vision-model-v1",
        "task_description": "Test task",
        "current_step": 1,
        "is_complete": False,
        "actions": [
            {
                "type": ActionType.CLICK,
                "argument": "500, 300",
                "count": 1,
            }
        ],
        "reason": "Test reason",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
    }


class TestAsyncClientInitialization:
    @pytest.mark.asyncio
    async def test_init_with_params(self):
        client = AsyncClient(base_url="https://api.test.com", api_key="test-key")
        assert client.base_url == "https://api.test.com"
        assert client.api_key == "test-key"
        await client.close()

    @pytest.mark.asyncio
    async def test_init_from_env(self, api_env):
        client = AsyncClient()
        assert client.base_url == api_env["base_url"]
        assert client.api_key == api_env["api_key"]
        await client.close()

    @pytest.mark.asyncio
    async def test_init_missing_base_url(self, monkeypatch):
        monkeypatch.delenv("OAGI_BASE_URL", raising=False)
        with pytest.raises(ConfigurationError):
            AsyncClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_init_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("OAGI_API_KEY", raising=False)
        with pytest.raises(ConfigurationError):
            AsyncClient(base_url="https://api.test.com")


class TestAsyncClientContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self, api_env):
        async with AsyncClient() as client:
            assert client.base_url == api_env["base_url"]
            assert client.api_key == api_env["api_key"]


class TestAsyncClientCreateMessage:
    @pytest.mark.asyncio
    async def test_create_message_success(self, async_client, mock_response_data):
        with patch.object(
            async_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value = mock_response

            result = await async_client.create_message(
                model="vision-model-v1",
                screenshot="base64-encoded-data",
                task_description="Test task",
            )

            assert isinstance(result, LLMResponse)
            assert result.task_id == "task-123"
            assert len(result.actions) == 1
            assert result.actions[0].type == ActionType.CLICK

    @pytest.mark.asyncio
    async def test_create_message_timeout(self, async_client):
        with patch.object(
            async_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")

            with pytest.raises(RequestTimeoutError):
                await async_client.create_message(
                    model="vision-model-v1",
                    screenshot="base64-data",
                    task_description="Test",
                )

    @pytest.mark.asyncio
    async def test_create_message_network_error(self, async_client):
        with patch.object(
            async_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.NetworkError("Network error")

            with pytest.raises(NetworkError):
                await async_client.create_message(
                    model="vision-model-v1",
                    screenshot="base64-data",
                    task_description="Test",
                )

    @pytest.mark.asyncio
    async def test_create_message_api_error(self, async_client):
        with patch.object(
            async_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "error": {"code": "unauthorized", "message": "Invalid API key"}
            }
            mock_post.return_value = mock_response

            with pytest.raises(AuthenticationError) as exc_info:
                await async_client.create_message(
                    model="vision-model-v1",
                    screenshot="base64-data",
                    task_description="Test",
                )
            assert "Invalid API key" in str(exc_info.value)


class TestAsyncClientHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self, async_client):
        with patch.object(
            async_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = await async_client.health_check()
            assert result == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_health_check_failure(self, async_client):
        with patch.object(
            async_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Error", request=Mock(), response=Mock()
            )
            mock_get.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                await async_client.health_check()
