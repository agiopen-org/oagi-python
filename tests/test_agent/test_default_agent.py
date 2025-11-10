"""Tests for default agent implementations."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from oagi.agent import AsyncDefaultAgent, DefaultAgent
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
    provider.return_value = Mock(read=lambda: b"test_image_bytes")
    provider.last_image.return_value = Mock(read=lambda: b"last_image_bytes")
    return provider


class TestDefaultAgent:
    def test_execute_success(self, mock_action_handler, mock_image_provider):
        with patch("oagi.agent.default.ShortTask") as mock_task_class:
            mock_task = Mock()
            mock_task_class.return_value = mock_task

            # Mock successful completion on first step
            mock_task.step.return_value = Step(
                reason="Clicking button",
                actions=[Action(type=ActionType.CLICK, argument="500,300")],
                stop=True,
            )

            agent = DefaultAgent(max_steps=5)
            success = agent.execute(
                "Click the button",
                mock_action_handler,
                mock_image_provider,
            )

            assert success is True
            mock_task.init_task.assert_called_once_with("Click the button", max_steps=5)
            mock_task.step.assert_called_once()
            mock_action_handler.assert_called_once()

    def test_execute_max_steps_reached(self, mock_action_handler, mock_image_provider):
        with patch("oagi.agent.default.ShortTask") as mock_task_class:
            mock_task = Mock()
            mock_task_class.return_value = mock_task

            # Mock never completing
            mock_task.step.return_value = Step(
                reason="Still working",
                actions=[Action(type=ActionType.WAIT, argument="1000")],
                stop=False,
            )

            agent = DefaultAgent(max_steps=3)
            success = agent.execute(
                "Complex task",
                mock_action_handler,
                mock_image_provider,
            )

            assert success is False
            assert mock_task.step.call_count == 3
            assert mock_action_handler.call_count == 3


@pytest.mark.asyncio
class TestAsyncDefaultAgent:
    async def test_execute_success(
        self, mock_async_action_handler, mock_async_image_provider
    ):
        with patch("oagi.agent.default.AsyncShortTask") as mock_task_class:
            mock_task = AsyncMock()
            mock_task_class.return_value = mock_task

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
            mock_task.init_task.assert_called_once()
            assert mock_task.step.call_count == 2
            assert mock_async_action_handler.call_count == 2

    async def test_execute_with_temperature(
        self, mock_async_action_handler, mock_async_image_provider
    ):
        with patch("oagi.agent.default.AsyncShortTask") as mock_task_class:
            mock_task = AsyncMock()
            mock_task_class.return_value = mock_task

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
