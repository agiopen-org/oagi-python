# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from oagi.client import AsyncClient
from oagi.constants import MODEL_ACTOR
from oagi.exceptions import (
    ConfigurationError,
)
from oagi.types import Step
from oagi.types.models import (
    UploadFileResponse,
    Usage,
)


@pytest_asyncio.fixture
async def test_client(api_env):
    with patch("oagi.client.async_.AsyncOpenAI"):
        client = AsyncClient(base_url=api_env["base_url"], api_key=api_env["api_key"])
        yield client


@pytest.fixture
def create_client():
    """Helper fixture to create and cleanup clients in tests."""

    def _create_client(*args, **kwargs):
        with patch("oagi.client.async_.AsyncOpenAI"):
            client = AsyncClient(*args, **kwargs)
            return client

    yield _create_client


class TestAsyncClientInit:
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
        ],
    )
    def test_init_missing_config_raises_error(
        self, missing_param, provided_param, error_message
    ):
        with pytest.raises(ConfigurationError, match=error_message):
            with patch("oagi.client.async_.AsyncOpenAI"):
                AsyncClient(**provided_param)

    def test_base_url_strips_trailing_slash(self, create_client):
        client = create_client(base_url="https://api.example.com/", api_key="test-key")
        assert client.base_url == "https://api.example.com"


class TestAsyncClientChatCompletion:
    @pytest.mark.asyncio
    async def test_chat_completion_success(
        self, test_client, sample_raw_output, sample_usage
    ):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = sample_raw_output
        mock_response.usage = Mock(
            prompt_tokens=sample_usage["prompt_tokens"],
            completion_tokens=sample_usage["completion_tokens"],
            total_tokens=sample_usage["total_tokens"],
        )
        test_client.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Test prompt"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/screenshot.png"},
                    },
                ],
            }
        ]

        step, raw_output, usage = await test_client.chat_completion(
            model=MODEL_ACTOR,
            messages=messages,
        )

        test_client.openai_client.chat.completions.create.assert_called_once()
        assert isinstance(step, Step)
        assert raw_output == sample_raw_output
        assert isinstance(usage, Usage)
        assert usage.prompt_tokens == sample_usage["prompt_tokens"]

    @pytest.mark.asyncio
    async def test_chat_completion_with_history(
        self, test_client, sample_raw_output, sample_usage
    ):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = sample_raw_output
        mock_response.usage = Mock(
            prompt_tokens=sample_usage["prompt_tokens"],
            completion_tokens=sample_usage["completion_tokens"],
            total_tokens=sample_usage["total_tokens"],
        )
        test_client.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        messages = [
            {"role": "user", "content": [{"type": "text", "text": "First message"}]},
            {"role": "assistant", "content": "previous response"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/screenshot.png"},
                    }
                ],
            },
        ]

        step, raw_output, usage = await test_client.chat_completion(
            model=MODEL_ACTOR,
            messages=messages,
        )

        call_args = test_client.openai_client.chat.completions.create.call_args
        sent_messages = call_args[1]["messages"]
        assert len(sent_messages) == 3

    @pytest.mark.asyncio
    async def test_chat_completion_with_temperature(
        self, test_client, sample_raw_output, sample_usage
    ):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = sample_raw_output
        mock_response.usage = Mock(
            prompt_tokens=sample_usage["prompt_tokens"],
            completion_tokens=sample_usage["completion_tokens"],
            total_tokens=sample_usage["total_tokens"],
        )
        test_client.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        messages = [{"role": "user", "content": "Test"}]

        step, raw_output, usage = await test_client.chat_completion(
            model=MODEL_ACTOR,
            messages=messages,
            temperature=0.7,
        )

        call_args = test_client.openai_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.7


class TestAsyncClientS3Upload:
    @pytest.mark.asyncio
    async def test_get_s3_presigned_url(self, test_client, upload_file_response):
        """Test getting S3 presigned URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = upload_file_response
        test_client.http_client.get = AsyncMock(return_value=mock_response)

        result = await test_client.get_s3_presigned_url()

        assert isinstance(result, UploadFileResponse)
        assert result.url == upload_file_response["url"]
        assert result.download_url == upload_file_response["download_url"]

    @pytest.mark.asyncio
    async def test_upload_to_s3(self, test_client):
        """Test uploading to S3."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        test_client.upload_client.put = AsyncMock(return_value=mock_response)

        # Should not raise
        await test_client.upload_to_s3(
            url="https://s3.amazonaws.com/presigned-url",
            content=b"image bytes",
        )

        test_client.upload_client.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_put_s3_presigned_url(self, test_client, upload_file_response):
        """Test combined get URL and upload."""
        # Mock get presigned URL
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = upload_file_response
        test_client.http_client.get = AsyncMock(return_value=mock_get_response)

        # Mock S3 upload
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put_response.raise_for_status.return_value = None
        test_client.upload_client.put = AsyncMock(return_value=mock_put_response)

        result = await test_client.put_s3_presigned_url(screenshot=b"image bytes")

        assert isinstance(result, UploadFileResponse)
        assert result.download_url == upload_file_response["download_url"]


class TestAsyncClientContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self, api_env):
        """Test client can be used as async context manager."""
        with patch("oagi.client.async_.AsyncOpenAI") as mock_openai:
            mock_openai_instance = Mock()
            mock_openai_instance.close = AsyncMock()
            mock_openai.return_value = mock_openai_instance

            async with AsyncClient(
                base_url=api_env["base_url"], api_key=api_env["api_key"]
            ) as client:
                # Mock the httpx clients' aclose methods
                client.http_client.aclose = AsyncMock()
                client.upload_client.aclose = AsyncMock()
                assert client.api_key == api_env["api_key"]

    @pytest.mark.asyncio
    async def test_close_closes_all_clients(self, test_client):
        """Test close() closes all underlying clients."""
        test_client.openai_client.close = AsyncMock()
        test_client.http_client.aclose = AsyncMock()
        test_client.upload_client.aclose = AsyncMock()

        await test_client.close()

        test_client.openai_client.close.assert_called_once()
        test_client.http_client.aclose.assert_called_once()
        test_client.upload_client.aclose.assert_called_once()
