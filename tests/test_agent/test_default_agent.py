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
        with patch("oagi.agent.default.AsyncActor") as mock_actor_class:
            mock_actor = AsyncMock()
            mock_actor_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_actor
            )
            mock_actor_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock successful completion on second step
            mock_actor.step.side_effect = [
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
            mock_actor.init_task.assert_called_once_with(
                "Click the button", max_steps=5
            )
            assert mock_actor.step.call_count == 2
            assert mock_async_action_handler.call_count == 2

    async def test_execute_with_temperature(
        self, mock_async_action_handler, mock_async_image_provider
    ):
        with patch("oagi.agent.default.AsyncActor") as mock_actor_class:
            mock_actor = AsyncMock()
            mock_actor_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_actor
            )
            mock_actor_class.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_actor.step.return_value = Step(reason="Done", actions=[], stop=True)

            agent = AsyncDefaultAgent(max_steps=5, temperature=0.7)
            success = await agent.execute(
                "Task with temperature",
                mock_async_action_handler,
                mock_async_image_provider,
            )

            assert success is True
            mock_actor.step.assert_called_with(
                mock_async_image_provider.return_value, temperature=0.7
            )

    async def test_execute_with_empty_actions_step(
        self, mock_async_action_handler, mock_async_image_provider
    ):
        """Test that steps with reasoning but no actions are tracked by observer."""
        step_observer = AsyncMock()

        with patch("oagi.agent.default.AsyncActor") as mock_actor_class:
            mock_actor = AsyncMock()
            mock_actor_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_actor
            )
            mock_actor_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock step with reasoning but no actions
            mock_actor.step.return_value = Step(
                reason="Analyzing the screen to plan next action",
                actions=[],  # Empty actions list
                stop=True,
            )

            agent = AsyncDefaultAgent(max_steps=5, step_observer=step_observer)
            success = await agent.execute(
                "Test task",
                mock_async_action_handler,
                mock_async_image_provider,
            )

            assert success is True
            # Verify observer was called even with empty actions
            step_observer.on_step.assert_called_once_with(
                1, "Analyzing the screen to plan next action", []
            )
            # Verify action handler was not called since there are no actions
            mock_async_action_handler.assert_not_called()
