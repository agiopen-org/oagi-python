"""Tests for Socket.IO agent wrappers."""

from unittest.mock import AsyncMock, Mock

import pytest

from oagi.server.agent_wrappers import SocketIOActionHandler, SocketIOImageProvider
from oagi.types import Action, ActionType, URLImage


@pytest.fixture
def mock_namespace():
    namespace = AsyncMock()
    namespace._emit_actions = AsyncMock()
    namespace.call = AsyncMock()
    namespace.config = Mock(socketio_timeout=30.0)
    return namespace


@pytest.fixture
def mock_session():
    session = Mock()
    session.session_id = "test_session_123"
    session.socket_id = "socket_456"
    session.current_screenshot_url = None
    return session


@pytest.fixture
def mock_oagi_client():
    client = AsyncMock()
    upload_response = Mock()
    upload_response.url = "https://s3.example.com/presigned"
    upload_response.uuid = "uuid-123"
    upload_response.expires_at = "2024-01-01T00:00:00Z"
    upload_response.download_url = "https://s3.example.com/download/uuid-123"
    client.get_s3_presigned_url.return_value = upload_response
    return client


class TestSocketIOActionHandler:
    @pytest.mark.asyncio
    async def test_execute_actions(self, mock_namespace, mock_session):
        handler = SocketIOActionHandler(mock_namespace, mock_session)

        actions = [
            Action(type=ActionType.CLICK, argument="500,300"),
            Action(type=ActionType.TYPE, argument="Hello"),
        ]

        await handler(actions)

        mock_namespace._emit_actions.assert_called_once_with(mock_session, actions)

    @pytest.mark.asyncio
    async def test_execute_empty_actions(self, mock_namespace, mock_session):
        handler = SocketIOActionHandler(mock_namespace, mock_session)

        await handler([])

        mock_namespace._emit_actions.assert_not_called()


class TestSocketIOImageProvider:
    @pytest.mark.asyncio
    async def test_capture_screenshot_success(
        self, mock_namespace, mock_session, mock_oagi_client
    ):
        # Setup successful screenshot response
        mock_namespace.call.return_value = {"success": True}

        provider = SocketIOImageProvider(mock_namespace, mock_session, mock_oagi_client)

        image = await provider()

        assert isinstance(image, URLImage)
        assert image.url == "https://s3.example.com/download/uuid-123"
        assert (
            mock_session.current_screenshot_url
            == "https://s3.example.com/download/uuid-123"
        )
        mock_oagi_client.get_s3_presigned_url.assert_called_once()
        mock_namespace.call.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_screenshot_failure(
        self, mock_namespace, mock_session, mock_oagi_client
    ):
        # Setup failed screenshot response
        mock_namespace.call.return_value = {"success": False, "error": "Upload failed"}

        provider = SocketIOImageProvider(mock_namespace, mock_session, mock_oagi_client)

        with pytest.raises(Exception, match="Screenshot upload failed: Upload failed"):
            await provider()

    @pytest.mark.asyncio
    async def test_capture_screenshot_no_response(
        self, mock_namespace, mock_session, mock_oagi_client
    ):
        # Setup no response
        mock_namespace.call.return_value = None

        provider = SocketIOImageProvider(mock_namespace, mock_session, mock_oagi_client)

        with pytest.raises(Exception, match="No response from screenshot request"):
            await provider()

    @pytest.mark.asyncio
    async def test_last_image_with_cached(
        self, mock_namespace, mock_session, mock_oagi_client
    ):
        provider = SocketIOImageProvider(mock_namespace, mock_session, mock_oagi_client)

        # Set cached URL
        provider._last_url = "https://s3.example.com/cached/image.png"

        image = await provider.last_image()

        assert isinstance(image, URLImage)
        assert image.url == "https://s3.example.com/cached/image.png"
        mock_namespace.call.assert_not_called()

    @pytest.mark.asyncio
    async def test_last_image_without_cached(
        self, mock_namespace, mock_session, mock_oagi_client
    ):
        # Setup successful screenshot response for fallback
        mock_namespace.call.return_value = {"success": True}

        provider = SocketIOImageProvider(mock_namespace, mock_session, mock_oagi_client)

        image = await provider.last_image()

        assert isinstance(image, URLImage)
        assert image.url == "https://s3.example.com/download/uuid-123"
        mock_namespace.call.assert_called_once()
