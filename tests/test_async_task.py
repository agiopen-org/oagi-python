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

from oagi.async_short_task import AsyncShortTask
from oagi.async_task import AsyncTask
from oagi.types import Action, ActionType, Step


@pytest_asyncio.fixture
async def async_task(api_env):
    task = AsyncTask(
        base_url=api_env["base_url"],
        api_key=api_env["api_key"],
        model="vision-model-v1",
    )
    yield task
    await task.close()


@pytest.fixture
def mock_llm_response():
    response = Mock()
    response.task_id = "task-123"
    response.reason = "Test reason"
    response.actions = [Action(type=ActionType.CLICK, argument="500, 300", count=1)]
    response.is_complete = False
    response.current_step = 1
    return response


class TestAsyncTaskInitialization:
    @pytest.mark.asyncio
    async def test_init_task(self, async_task, mock_llm_response):
        with patch.object(
            async_task.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_llm_response

            await async_task.init_task("Test task description")

            assert async_task.task_description == "Test task description"
            assert async_task.task_id == "task-123"
            mock_create.assert_called_once_with(
                model="vision-model-v1",
                screenshot="",
                task_description="Test task description",
                task_id=None,
            )


class TestAsyncTaskStep:
    @pytest.mark.asyncio
    async def test_step_with_bytes(self, async_task, mock_llm_response):
        async_task.task_description = "Test task"
        async_task.task_id = "task-123"

        with patch.object(
            async_task.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_llm_response

            screenshot_bytes = b"test-image-data"
            result = await async_task.step(screenshot_bytes)

            assert isinstance(result, Step)
            assert result.reason == "Test reason"
            assert len(result.actions) == 1
            assert result.stop is False

    @pytest.mark.asyncio
    async def test_step_without_init(self, async_task):
        with pytest.raises(ValueError) as exc_info:
            await async_task.step(b"test-image")
        assert "Call init_task() first" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_step_with_instruction(self, async_task, mock_llm_response):
        async_task.task_description = "Test task"
        async_task.task_id = "task-123"

        with patch.object(
            async_task.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_llm_response

            await async_task.step(b"test-image", instruction="Click the button")

            # Verify instruction was passed
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["instruction"] == "Click the button"

    @pytest.mark.asyncio
    async def test_step_task_complete(self, async_task):
        async_task.task_description = "Test task"

        complete_response = Mock()
        complete_response.task_id = "task-123"
        complete_response.reason = "Task completed"
        complete_response.actions = []
        complete_response.is_complete = True
        complete_response.current_step = 2

        with patch.object(
            async_task.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = complete_response

            result = await async_task.step(b"test-image")

            assert result.stop is True
            assert result.reason == "Task completed"


class TestAsyncTaskContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self, api_env):
        async with AsyncTask(
            base_url=api_env["base_url"], api_key=api_env["api_key"]
        ) as task:
            assert task.task_id is None
            assert task.task_description is None


class TestAsyncShortTask:
    @pytest.mark.asyncio
    async def test_auto_mode_success(self, api_env):
        task = AsyncShortTask(base_url=api_env["base_url"], api_key=api_env["api_key"])

        # Mock responses for auto mode
        init_response = Mock()
        init_response.task_id = "task-123"

        step_response = Mock()
        step_response.task_id = "task-123"
        step_response.reason = "Clicking button"
        step_response.actions = [
            Action(type=ActionType.CLICK, argument="500, 300", count=1)
        ]
        step_response.is_complete = False
        step_response.current_step = 1

        complete_response = Mock()
        complete_response.task_id = "task-123"
        complete_response.reason = "Task complete"
        complete_response.actions = []
        complete_response.is_complete = True
        complete_response.current_step = 2

        # Mock image provider and executor
        mock_image_provider = AsyncMock()
        mock_image_provider.return_value = Mock(read=lambda: b"test-image")

        mock_executor = AsyncMock()

        with patch.object(
            task.client, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = [init_response, step_response, complete_response]

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
        response.current_step = 1

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
