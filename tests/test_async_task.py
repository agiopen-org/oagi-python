# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from oagi.task import AsyncActor, AsyncShortTask
from oagi.types import Action, ActionType, Step


@pytest_asyncio.fixture
async def async_actor(api_env):
    actor = AsyncActor(
        base_url=api_env["base_url"],
        api_key=api_env["api_key"],
        model="vision-model-v1",
    )
    yield actor
    await actor.close()


@pytest.fixture
def mock_llm_response():
    response = Mock()
    response.reason = "Test reason"
    response.actions = [Action(type=ActionType.CLICK, argument="500, 300", count=1)]
    response.is_complete = False
    return response


class TestAsyncActorInitialization:
    @pytest.mark.asyncio
    async def test_init_task(self, async_actor, mock_llm_response):
        # V2 API: init_task doesn't make API call, just sets description
        original_task_id = async_actor.task_id

        await async_actor.init_task("Test task description")

        assert async_actor.task_description == "Test task description"
        # V2 API: task_id is regenerated on init_task to create a fresh task
        assert async_actor.task_id != original_task_id
        assert isinstance(async_actor.task_id, str)
        assert len(async_actor.task_id) == 32  # UUID hex without dashes


class TestAsyncActorStep:
    @pytest.mark.asyncio
    async def test_step_with_bytes(self, async_actor, mock_llm_response):
        async_actor.task_description = "Test task"
        async_actor.task_id = "task-123"

        with patch.object(
            async_actor.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_llm_response

            screenshot_bytes = b"test-image-data"
            result = await async_actor.step(screenshot_bytes)

            assert isinstance(result, Step)
            assert result.reason == "Test reason"
            assert len(result.actions) == 1
            assert result.stop is False

    @pytest.mark.asyncio
    async def test_step_without_init(self, async_actor):
        with pytest.raises(ValueError) as exc_info:
            await async_actor.step(b"test-image")
        assert "Call init_task() first" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_step_with_instruction(self, async_actor, mock_llm_response):
        async_actor.task_description = "Test task"
        async_actor.task_id = "task-123"

        with patch.object(
            async_actor.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_llm_response

            await async_actor.step(b"test-image", instruction="Click the button")

            # Verify instruction was passed
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["instruction"] == "Click the button"

    @pytest.mark.asyncio
    async def test_step_task_complete(self, async_actor):
        async_actor.task_description = "Test task"

        complete_response = Mock()
        complete_response.task_id = "task-123"
        complete_response.reason = "Task completed"
        complete_response.actions = []
        complete_response.is_complete = True

        with patch.object(
            async_actor.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = complete_response

            result = await async_actor.step(b"test-image")

            assert result.stop is True
            assert result.reason == "Task completed"


class TestAsyncActorContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self, api_env):
        async with AsyncActor(
            base_url=api_env["base_url"], api_key=api_env["api_key"]
        ) as actor:
            # V2 API: task_id is generated as UUID on init
            assert actor.task_id is not None
            assert isinstance(actor.task_id, str)
            assert len(actor.task_id) == 32  # UUID hex without dashes
            assert actor.task_description is None


class TestAsyncShortTask:
    @pytest.mark.asyncio
    async def test_auto_mode_success(self, api_env):
        task = AsyncShortTask(base_url=api_env["base_url"], api_key=api_env["api_key"])

        # V2 API: Mock responses for steps only (no init_task call)
        step_response = Mock()
        step_response.task_id = "task-123"
        step_response.reason = "Clicking button"
        step_response.actions = [
            Action(type=ActionType.CLICK, argument="500, 300", count=1)
        ]
        step_response.is_complete = False
        step_response.raw_output = "Clicking the button"

        complete_response = Mock()
        complete_response.task_id = "task-123"
        complete_response.reason = "Task complete"
        complete_response.actions = []
        complete_response.is_complete = True
        complete_response.raw_output = "Task is complete"

        # Mock image provider and executor
        mock_image_provider = AsyncMock()
        mock_image_provider.return_value = Mock(read=lambda: b"test-image")

        mock_executor = AsyncMock()

        with patch.object(
            task.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            # V2 API: Only step responses (no init response)
            mock_create.side_effect = [step_response, complete_response]

            result = await task.auto_mode(
                "Test task",
                max_steps=5,
                executor=mock_executor,
                image_provider=mock_image_provider,
            )

            assert result is True
            assert (
                mock_executor.call_count == 2
            )  # Called for both steps including the completed one
            assert mock_image_provider.call_count == 2

        await task.close()

    @pytest.mark.asyncio
    async def test_auto_mode_max_steps_reached(self, api_env):
        task = AsyncShortTask(base_url=api_env["base_url"], api_key=api_env["api_key"])

        # Mock response that never completes
        response = Mock()
        response.task_id = "task-123"
        response.reason = "Still working"
        response.actions = [Action(type=ActionType.WAIT, argument="", count=1)]
        response.is_complete = False
        response.raw_output = "Still working on it"

        mock_image_provider = AsyncMock()
        mock_image_provider.return_value = Mock(read=lambda: b"test-image")

        mock_executor = AsyncMock()

        with patch.object(
            task.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = response

            result = await task.auto_mode(
                "Test task",
                max_steps=3,
                executor=mock_executor,
                image_provider=mock_image_provider,
            )

            assert result is False
            assert mock_executor.call_count == 3

        await task.close()


class TestAsyncActorTemperature:
    @pytest.mark.asyncio
    async def test_async_task_temperature_fallback(self, api_env, mock_llm_response):
        """Test that temperature fallback works: step temp -> actor temp -> None."""
        actor = AsyncActor(
            api_key=api_env["api_key"],
            base_url=api_env["base_url"],
            temperature=0.5,
        )
        actor.task_description = "Test task"

        with patch.object(
            actor.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_llm_response

            # Step with override temperature
            await actor.step(b"screenshot_data", temperature=0.8)

            # Verify step temperature (0.8) is used
            call_args = mock_create.call_args
            assert call_args[1]["temperature"] == 0.8

            # Step without temperature - should use actor default (0.5)
            await actor.step(b"screenshot_data2")

            call_args = mock_create.call_args
            assert call_args[1]["temperature"] == 0.5

        await actor.close()
