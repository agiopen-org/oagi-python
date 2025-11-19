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

from oagi.client import AsyncClient
from oagi.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    RequestTimeoutError,
)
from oagi.types import ActionType
from oagi.types.models import LLMResponse, UploadFileResponse


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
        client = AsyncClient(api_key="test-key")
        assert client.base_url == "https://api.agiopen.org"
        await client.close()

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
    async def test_create_message_success(
        self,
        async_client,
        mock_response_data,
        mock_upload_response,
        upload_file_response,
    ):
        # Mock S3 upload flow
        with patch.object(
            async_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_upload_response

            with patch.object(async_client, "upload_client") as mock_upload_client:
                mock_s3_response = Mock()
                mock_s3_response.raise_for_status = AsyncMock()
                mock_upload_client.put = AsyncMock(return_value=mock_s3_response)

                with patch.object(
                    async_client.client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = mock_response_data
                    mock_post.return_value = mock_response

                    result = await async_client.create_message(
                        model="vision-model-v1",
                        screenshot=b"image_data",
                        task_description="Test task",
                    )

                    assert isinstance(result, LLMResponse)
                    assert len(result.actions) == 1
                    assert result.actions[0].type == ActionType.CLICK

                    # Verify S3 upload flow
                    mock_get.assert_called_once()
                    mock_upload_client.put.assert_called_once()

                    # Verify /v2/message call with OpenAI format
                    call_args = mock_post.call_args
                    assert call_args[0][0] == "/v2/message"
                    payload = call_args[1]["json"]
                    assert "messages" in payload
                    assert payload["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_create_message_with_temperature(
        self, async_client, mock_response_data, mock_upload_response
    ):
        # Mock S3 upload flow
        with patch.object(
            async_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_upload_response

            with patch.object(async_client, "upload_client") as mock_upload_client:
                mock_s3_response = Mock()
                mock_s3_response.raise_for_status = AsyncMock()
                mock_upload_client.put = AsyncMock(return_value=mock_s3_response)

                with patch.object(
                    async_client.client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = mock_response_data
                    mock_post.return_value = mock_response

                    await async_client.create_message(
                        model="vision-model-v1",
                        screenshot=b"base64-data",
                        task_description="Test task",
                        temperature=0.5,
                    )

                    # Verify temperature is included in payload
                    mock_post.assert_called_once()
                    call_args = mock_post.call_args
                    payload = call_args[1]["json"]
                    assert payload["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_create_message_timeout(self, async_client, mock_upload_response):
        # Mock S3 upload flow (succeeds)
        with patch.object(
            async_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_upload_response

            with patch.object(async_client, "upload_client") as mock_upload_client:
                mock_s3_response = Mock()
                mock_s3_response.raise_for_status = AsyncMock()
                mock_upload_client.put = AsyncMock(return_value=mock_s3_response)

                # /v2/message call times out
                with patch.object(
                    async_client.client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_post.side_effect = httpx.TimeoutException("Timeout")

                    with pytest.raises(RequestTimeoutError):
                        await async_client.create_message(
                            model="vision-model-v1",
                            screenshot=b"image_data",
                            task_description="Test",
                        )

    @pytest.mark.asyncio
    async def test_create_message_network_error(
        self, async_client, mock_upload_response
    ):
        # Mock S3 upload flow (succeeds)
        with patch.object(
            async_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_upload_response

            with patch.object(async_client, "upload_client") as mock_upload_client:
                mock_s3_response = Mock()
                mock_s3_response.raise_for_status = AsyncMock()
                mock_upload_client.put = AsyncMock(return_value=mock_s3_response)

                # /v2/message call has network error
                with patch.object(
                    async_client.client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_post.side_effect = httpx.NetworkError("Network error")

                    with pytest.raises(NetworkError):
                        await async_client.create_message(
                            model="vision-model-v1",
                            screenshot=b"image-data",
                            task_description="Test",
                        )

    @pytest.mark.asyncio
    async def test_create_message_api_error(self, async_client, mock_upload_response):
        # Mock S3 upload flow (succeeds)
        with patch.object(
            async_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_upload_response

            with patch.object(async_client, "upload_client") as mock_upload_client:
                mock_s3_response = Mock()
                mock_s3_response.raise_for_status = AsyncMock()
                mock_upload_client.put = AsyncMock(return_value=mock_s3_response)

                # /v2/message returns error
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
                            screenshot=b"image-data",
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


class TestAsyncClientS3Upload:
    @pytest.mark.asyncio
    async def test_get_s3_presigned_url_success(
        self, async_client, mock_upload_response, upload_file_response
    ):
        with patch.object(
            async_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_upload_response

            result = await async_client.get_s3_presigned_url(api_version="v1.2")

            assert isinstance(result, UploadFileResponse)
            assert result.url == upload_file_response["url"]
            assert result.uuid == upload_file_response["uuid"]
            mock_get.assert_called_once_with(
                "/v1/file/upload",
                headers={"x-api-key": "test-key", "x-api-version": "v1.2"},
                timeout=60,
            )

    @pytest.mark.asyncio
    async def test_upload_to_s3_success(self, async_client):
        with patch.object(async_client, "upload_client") as mock_upload_client:
            mock_response = Mock()
            mock_response.raise_for_status = AsyncMock()
            mock_upload_client.put = AsyncMock(return_value=mock_response)

            await async_client.upload_to_s3(
                url="https://s3.amazonaws.com/test", content=b"test content"
            )

            mock_upload_client.put.assert_called_once_with(
                url="https://s3.amazonaws.com/test", content=b"test content"
            )
            mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_put_s3_presigned_url_success(
        self, async_client, mock_upload_response, upload_file_response
    ):
        with patch.object(
            async_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_upload_response

            with patch.object(async_client, "upload_client") as mock_upload_client:
                mock_s3_response = Mock()
                mock_s3_response.raise_for_status = AsyncMock()
                mock_upload_client.put = AsyncMock(return_value=mock_s3_response)

                result = await async_client.put_s3_presigned_url(
                    screenshot=b"test screenshot", api_version="v1.2"
                )

                assert isinstance(result, UploadFileResponse)
                assert result.url == upload_file_response["url"]
                # Verify it called get presigned URL
                mock_get.assert_called_once()
                # Verify it uploaded to S3
                mock_upload_client.put.assert_called_once_with(
                    url=upload_file_response["url"], content=b"test screenshot"
                )
