"""Tests for Planner class."""

from unittest.mock import AsyncMock, patch

import pytest

from oagi.agent.tasker.memory import PlannerMemory
from oagi.agent.tasker.models import (
    Action,
    PlannerOutput,
    ReflectionOutput,
)
from oagi.agent.tasker.planner import Planner
from oagi.types.models.client import GenerateResponse, UploadFileResponse


class TestPlanner:
    @pytest.fixture
    def mock_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def planner(self, mock_client):
        return Planner(client=mock_client)

    @pytest.fixture
    def memory(self):
        memory = PlannerMemory()
        memory.set_task(
            task_description="Test task",
            todos=["Todo 1", "Todo 2"],
            deliverables=["Deliverable 1"],
        )
        return memory

    @pytest.mark.asyncio
    async def test_initial_plan_with_screenshot(self, planner, mock_client, memory):
        # Mock the client responses
        mock_client.put_s3_presigned_url.return_value = UploadFileResponse(
            url="https://s3.example.com/upload",
            uuid="test-uuid-123",
            expires_at=1234567890,
            file_expires_at=1234567890,
            download_url="https://s3.example.com/image.jpg",
        )
        mock_client.call_worker.return_value = GenerateResponse(
            response='{"reasoning": "Start with clicking", "subtask": "Click on button"}',
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.001,
        )

        screenshot = b"fake_image_bytes"
        result = await planner.initial_plan(
            todo="Click button",
            context={},
            screenshot=screenshot,
            memory=memory,
            todo_index=0,
        )

        assert isinstance(result, PlannerOutput)
        assert result.instruction == "Click on button"
        assert result.reasoning == "Start with clicking"
        mock_client.put_s3_presigned_url.assert_called_once_with(screenshot)
        mock_client.call_worker.assert_called_once()

    @pytest.mark.asyncio
    async def test_initial_plan_without_screenshot(self, planner, mock_client):
        mock_client.call_worker.return_value = GenerateResponse(
            response='{"reasoning": "No visual needed", "subtask": "Type text"}',
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.001,
        )

        result = await planner.initial_plan(
            todo="Type something",
            context={"task_description": "Test"},
            screenshot=None,
        )

        assert result.instruction == "Type text"
        assert result.reasoning == "No visual needed"
        mock_client.put_s3_presigned_url.assert_not_called()

    @pytest.mark.asyncio
    async def test_reflect_with_actions(self, planner, mock_client, memory):
        actions = [
            Action(
                timestamp="2024-01-01T00:00:00",
                action_type="click",
                target="(100, 200)",
            ),
            Action(
                timestamp="2024-01-01T00:00:01",
                action_type="type",
                details={"argument": "test"},
            ),
        ]

        mock_client.put_s3_presigned_url.return_value = UploadFileResponse(
            url="https://s3.example.com/upload2",
            uuid="test-uuid-456",
            expires_at=1234567890,
            file_expires_at=1234567890,
            download_url="https://s3.example.com/image2.jpg",
        )
        mock_client.call_worker.return_value = GenerateResponse(
            response='{"assessment": "Good progress", "success": "yes", "reflection": "Task completed", "subtask_instruction": ""}',
            prompt_tokens=150,
            completion_tokens=75,
            cost=0.002,
        )

        result = await planner.reflect(
            actions=actions,
            context={},
            screenshot=b"screenshot",
            memory=memory,
            todo_index=0,
            current_instruction="Click and type",
        )

        assert isinstance(result, ReflectionOutput)
        assert result.success_assessment is True
        assert result.reasoning == "Task completed"

    @pytest.mark.asyncio
    async def test_reflect_pivot_decision(self, planner, mock_client):
        mock_client.call_worker.return_value = GenerateResponse(
            response='{"success": "no", "subtask_instruction": "Try different approach", "reflection": "Need to pivot"}',
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.001,
        )

        result = await planner.reflect(
            actions=[],
            context={"current_todo": "Test todo"},
            screenshot=None,
        )

        assert result.continue_current is False
        assert result.new_instruction == "Try different approach"
        assert result.success_assessment is False

    @pytest.mark.asyncio
    async def test_summarize(self, planner, mock_client, memory):
        mock_client.call_worker.return_value = GenerateResponse(
            response='{"task_summary": "Successfully completed the task"}',
            prompt_tokens=80,
            completion_tokens=20,
            cost=0.001,
        )

        result = await planner.summarize(
            execution_history=[],
            context={},
            memory=memory,
            todo_index=0,
        )

        assert result == "Successfully completed the task"

    @pytest.mark.asyncio
    async def test_parse_planner_output_valid_json(self, planner):
        response = '{"reasoning": "Clear path", "subtask": "Click submit"}'
        output = planner._parse_planner_output(response)
        assert output.instruction == "Click submit"
        assert output.reasoning == "Clear path"

    @pytest.mark.asyncio
    async def test_parse_planner_output_fallback(self, planner):
        response = "Invalid JSON response"
        output = planner._parse_planner_output(response)
        assert output.instruction == response
        assert output.reasoning == "Failed to parse structured response"

    @pytest.mark.asyncio
    async def test_parse_reflection_output_valid(self, planner):
        response = (
            '{"success": "yes", "reflection": "All good", "subtask_instruction": ""}'
        )
        output = planner._parse_reflection_output(response)
        assert output.success_assessment is True
        assert output.reasoning == "All good"
        assert output.continue_current is False

    @pytest.mark.asyncio
    async def test_parse_reflection_output_fallback(self, planner):
        response = "Invalid JSON"
        output = planner._parse_reflection_output(response)
        assert output.continue_current is True
        assert output.new_instruction is None
        assert "Failed to parse" in output.reasoning

    @pytest.mark.asyncio
    async def test_ensure_client_creates_when_needed(self):
        planner = Planner(client=None)
        assert planner.client is None

        with patch("oagi.agent.tasker.planner.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance

            client = planner._ensure_client()
            assert client == mock_instance
            assert planner._owns_client is True

    @pytest.mark.asyncio
    async def test_close_owned_client(self):
        planner = Planner(client=None)
        mock_client = AsyncMock()
        planner.client = mock_client
        planner._owns_client = True

        await planner.close()
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_not_owned_client(self, mock_client):
        planner = Planner(client=mock_client)
        planner._owns_client = False

        await planner.close()
        mock_client.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with Planner() as planner:
            assert isinstance(planner, Planner)
