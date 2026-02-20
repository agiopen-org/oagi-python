# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from oagi.actor import AsyncActor
from oagi.types import Step


@pytest_asyncio.fixture
async def async_actor(api_env):
    with patch("oagi.client.async_.AsyncOpenAI"):
        actor = AsyncActor(
            base_url=api_env["base_url"],
            api_key=api_env["api_key"],
            model="vision-model-v1",
        )
        # Mock close methods as async
        actor.client.openai_client.close = AsyncMock()
        actor.client.http_client.aclose = AsyncMock()
        actor.client.upload_client.aclose = AsyncMock()
        yield actor
        await actor.close()


class TestAsyncActorInitialization:
    @pytest.mark.asyncio
    async def test_init_task(self, async_actor):
        original_task_id = async_actor.task_id

        await async_actor.init_task("Test task description")

        assert async_actor.task_description == "Test task description"
        assert async_actor.task_id != original_task_id
        assert isinstance(async_actor.task_id, str)
        assert len(async_actor.task_id) == 32


class TestAsyncActorStep:
    @pytest.mark.asyncio
    async def test_step_with_bytes(self, async_actor, sample_step, sample_usage_obj):
        async_actor.task_description = "Test task"
        async_actor.task_id = "task-123"

        async_actor.client.chat_completion = AsyncMock(
            return_value=(sample_step, "raw output", sample_usage_obj)
        )
        async_actor.client.put_s3_presigned_url = AsyncMock(
            return_value=AsyncMock(download_url="https://cdn.example.com/image.png")
        )

        result = await async_actor.step(b"test-image-data")

        assert isinstance(result, Step)
        assert result.reason == sample_step.reason
        assert len(result.actions) == 1
        assert result.stop is False

    @pytest.mark.asyncio
    async def test_step_without_init(self, async_actor):
        with pytest.raises(ValueError) as exc_info:
            await async_actor.step(b"test-image")
        assert "Call init_task() first" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_step_with_instruction(
        self, async_actor, sample_step, sample_usage_obj
    ):
        """Test that instruction parameter is accepted (though currently unused)."""
        async_actor.task_description = "Test task"
        async_actor.task_id = "task-123"

        async_actor.client.chat_completion = AsyncMock(
            return_value=(sample_step, "raw output", sample_usage_obj)
        )
        async_actor.client.put_s3_presigned_url = AsyncMock(
            return_value=AsyncMock(download_url="https://cdn.example.com/image.png")
        )

        result = await async_actor.step(b"test-image", instruction="Click the button")

        # Verify chat_completion was called
        async_actor.client.chat_completion.assert_called_once()
        assert isinstance(result, Step)
        assert not result.stop

    @pytest.mark.asyncio
    async def test_step_forwards_parser_mode(
        self, async_actor, sample_step, sample_usage_obj
    ):
        async_actor.task_description = "Test task"
        async_actor.task_id = "task-123"
        async_actor.client.chat_completion = AsyncMock(
            return_value=(sample_step, "raw output", sample_usage_obj)
        )
        async_actor.client.put_s3_presigned_url = AsyncMock(
            return_value=AsyncMock(download_url="https://cdn.example.com/image.png")
        )

        await async_actor.step(b"test-image", parser_mode="legacy")

        call_args = async_actor.client.chat_completion.call_args
        assert call_args[1]["parser_mode"] == "legacy"

    @pytest.mark.asyncio
    async def test_step_task_complete(
        self, async_actor, completed_step, sample_usage_obj
    ):
        async_actor.task_description = "Test task"
        async_actor.task_id = "task-123"

        async_actor.client.chat_completion = AsyncMock(
            return_value=(completed_step, "completed output", sample_usage_obj)
        )
        async_actor.client.put_s3_presigned_url = AsyncMock(
            return_value=AsyncMock(download_url="https://cdn.example.com/image.png")
        )

        result = await async_actor.step(b"test-image")

        assert result.stop is True
        assert result.reason == "The task has been completed successfully"

    @pytest.mark.asyncio
    async def test_step_raises_error_when_max_steps_reached(
        self, async_actor, sample_step, sample_usage_obj
    ):
        async_actor.client.chat_completion = AsyncMock(
            return_value=(sample_step, "raw output", sample_usage_obj)
        )
        async_actor.client.put_s3_presigned_url = AsyncMock(
            return_value=AsyncMock(download_url="https://cdn.example.com/image.png")
        )
        await async_actor.init_task("Test task", max_steps=3)

        # Execute 3 steps successfully
        for _ in range(3):
            await async_actor.step(b"test-image")

        # 4th step should raise error
        with pytest.raises(ValueError, match="Max steps limit \\(3\\) reached"):
            await async_actor.step(b"test-image")


class TestAsyncActorContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self, api_env):
        with patch("oagi.client.async_.AsyncOpenAI"):
            actor = AsyncActor(base_url=api_env["base_url"], api_key=api_env["api_key"])
            # Mock close methods as async
            actor.client.openai_client.close = AsyncMock()
            actor.client.http_client.aclose = AsyncMock()
            actor.client.upload_client.aclose = AsyncMock()

            async with actor:
                assert actor.task_id is not None
                assert isinstance(actor.task_id, str)
                assert len(actor.task_id) == 32
                assert actor.task_description is None


class TestAsyncActorTemperature:
    @pytest.mark.asyncio
    async def test_async_task_temperature_fallback(
        self, api_env, sample_step, sample_usage_obj
    ):
        with patch("oagi.client.async_.AsyncOpenAI"):
            actor = AsyncActor(
                api_key=api_env["api_key"],
                base_url=api_env["base_url"],
                temperature=0.5,
            )
            actor.task_description = "Test task"

            # Mock close methods as async
            actor.client.openai_client.close = AsyncMock()
            actor.client.http_client.aclose = AsyncMock()
            actor.client.upload_client.aclose = AsyncMock()

            actor.client.chat_completion = AsyncMock(
                return_value=(sample_step, "raw output", sample_usage_obj)
            )
            actor.client.put_s3_presigned_url = AsyncMock(
                return_value=AsyncMock(download_url="https://cdn.example.com/image.png")
            )

            # Step with override temperature
            await actor.step(b"screenshot_data", temperature=0.8)

            # Verify step temperature (0.8) is used
            call_args = actor.client.chat_completion.call_args
            assert call_args[1]["temperature"] == 0.8

            # Step without temperature - should use actor default (0.5)
            await actor.step(b"screenshot_data2")

            call_args = actor.client.chat_completion.call_args
            assert call_args[1]["temperature"] == 0.5

            await actor.close()
