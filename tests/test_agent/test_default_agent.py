"""Tests for default agent implementations."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from oagi.agent import AsyncDefaultAgent
from oagi.types import Action, ActionType
from oagi.types.models.step import Step


@pytest.fixture
def mock_action_handler():
    return Mock()


@pytest.fixture
def mock_image_provider():
    provider = Mock()
    provider.return_value = Mock(read=lambda: b"test_image_bytes")
    provider.last_image.return_value = Mock(read=lambda: b"last_image_bytes")
    return provider


@pytest.fixture
def mock_async_action_handler():
    return AsyncMock()


@pytest.fixture
def mock_async_image_provider():
    provider = AsyncMock()
    mock_image = Mock(read=lambda: b"test_image_bytes")
    mock_image.get_url.return_value = "https://example.com/image.png"
    provider.return_value = mock_image

    mock_last_image = Mock(read=lambda: b"last_image_bytes")
    mock_last_image.get_url.return_value = "https://example.com/last_image.png"
    provider.last_image.return_value = mock_last_image
    return provider


@pytest.mark.asyncio
class TestAsyncDefaultAgent:
    async def test_execute_success(
        self, mock_async_action_handler, mock_async_image_provider
    ):
        with patch("oagi.agent.default.AsyncTask") as mock_task_class:
            mock_task = AsyncMock()
            mock_task_class.return_value.__aenter__ = AsyncMock(return_value=mock_task)
            mock_task_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock successful completion on second step
            mock_task.step.side_effect = [
                Step(
                    reason="Moving to button",
                    actions=[Action(type=ActionType.SCROLL, argument="500,500,down")],
                    stop=False,
                ),
                Step(
                    reason="Clicking button",
                    actions=[Action(type=ActionType.CLICK, argument="500,300")],
                    stop=True,
                ),
            ]

            agent = AsyncDefaultAgent(max_steps=5)
            success = await agent.execute(
                "Click the button",
                mock_async_action_handler,
                mock_async_image_provider,
            )

            assert success is True
            mock_task.init_task.assert_called_once_with("Click the button", max_steps=5)
            assert mock_task.step.call_count == 2
            assert mock_async_action_handler.call_count == 2

    async def test_execute_with_temperature(
        self, mock_async_action_handler, mock_async_image_provider
    ):
        with patch("oagi.agent.default.AsyncTask") as mock_task_class:
            mock_task = AsyncMock()
            mock_task_class.return_value.__aenter__ = AsyncMock(return_value=mock_task)
            mock_task_class.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_task.step.return_value = Step(reason="Done", actions=[], stop=True)

            agent = AsyncDefaultAgent(max_steps=5, temperature=0.7)
            success = await agent.execute(
                "Task with temperature",
                mock_async_action_handler,
                mock_async_image_provider,
            )

            assert success is True
            mock_task.step.assert_called_with(
                mock_async_image_provider.return_value, temperature=0.7
            )
