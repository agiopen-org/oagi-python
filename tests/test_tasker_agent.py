"""Tests for the TaskerAgent."""

from unittest.mock import AsyncMock, patch

import pytest

from oagi.agent.tasker import TaskerAgent
from oagi.agent.tasker.models import (
    Action,
    ExecutionResult,
    TodoStatus,
)
from oagi.agent.tasker.planner import Planner


class MockPlanner(Planner):
    """Mock planner for testing."""

    async def _call_external_llm(self, prompt: str, image: bytes | None = None) -> str:
        """Mock LLM call that returns canned responses."""
        if "initial plan" in prompt.lower():
            return '{"instruction": "Test instruction", "reasoning": "Test reasoning", "subtodos": []}'
        elif "reflect" in prompt.lower():
            return '{"continue_current": true, "new_instruction": null, "reasoning": "Continue", "success_assessment": false}'
        else:
            return "Test summary"


@pytest.mark.asyncio
class TestTaskerAgent:
    """Test suite for TaskerAgent."""

    async def test_init(self):
        """Test TaskerAgent initialization."""
        agent = TaskerAgent(
            api_key="test-key",
            base_url="https://api.test.com",
            model="test-model",
            max_steps=50,
            temperature=0.5,
        )

        assert agent.api_key == "test-key"
        assert agent.base_url == "https://api.test.com"
        assert agent.model == "test-model"
        assert agent.max_steps == 50
        assert agent.temperature == 0.5
        assert agent.memory is not None
        assert agent.current_taskee_agent is None
        assert agent.current_todo_index == -1

    async def test_set_task(self):
        """Test setting task with todos and deliverables."""
        agent = TaskerAgent()
        todos = ["Todo 1", "Todo 2", "Todo 3"]
        deliverables = ["Deliverable 1", "Deliverable 2"]

        agent.set_task("Test task", todos, deliverables)

        assert agent.memory.task_description == "Test task"
        assert len(agent.memory.todos) == 3
        assert len(agent.memory.deliverables) == 2
        assert all(t.status == TodoStatus.PENDING for t in agent.memory.todos)

    async def test_prepare_with_no_todos(self):
        """Test prepare when no todos remain."""
        agent = TaskerAgent()
        agent.set_task("Test task", [], [])

        result = agent._prepare()
        assert result is None

    async def test_prepare_with_pending_todo(self):
        """Test prepare with pending todo."""
        agent = TaskerAgent(planner=MockPlanner())
        agent.set_task("Test task", ["Todo 1"], [])

        result = agent._prepare()
        assert result is not None

        todo, index = result
        assert todo.description == "Todo 1"
        assert index == 0
        assert agent.current_taskee_agent is not None
        assert agent.current_todo_index == 0
        assert agent.memory.todos[0].status == TodoStatus.IN_PROGRESS

    @patch("oagi.agent.tasker.taskee_agent.TaskeeAgent.execute")
    @patch("oagi.agent.tasker.taskee_agent.TaskeeAgent.return_execution_results")
    async def test_execute_single_todo(self, mock_return_results, mock_execute):
        """Test executing a single todo."""
        # Setup mocks
        mock_execute.return_value = True
        mock_return_results.return_value = ExecutionResult(
            success=True,
            actions=[
                Action(
                    timestamp="2024-01-01T00:00:00",
                    action_type="click",
                    target="button",
                )
            ],
            summary="Successfully completed",
            total_steps=1,
        )

        # Create agent and set task
        agent = TaskerAgent(planner=MockPlanner())
        agent.set_task("Test task", ["Todo 1"], [])

        # Create mock handlers
        action_handler = AsyncMock()
        image_provider = AsyncMock()
        image_provider.return_value = b"mock image"

        # Execute
        result = await agent.execute("Test task", action_handler, image_provider)

        assert result is True
        assert agent.memory.todos[0].status == TodoStatus.COMPLETED
        assert len(agent.memory.history) == 1
        assert agent.memory.history[0].completed is True

    @patch("oagi.agent.tasker.taskee_agent.TaskeeAgent.execute")
    @patch("oagi.agent.tasker.taskee_agent.TaskeeAgent.return_execution_results")
    async def test_execute_multiple_todos(self, mock_return_results, mock_execute):
        """Test executing multiple todos."""
        # Setup mocks to return success for all todos
        mock_execute.return_value = True
        mock_return_results.return_value = ExecutionResult(
            success=True,
            actions=[],
            summary="Completed",
            total_steps=1,
        )

        # Create agent and set task
        agent = TaskerAgent(planner=MockPlanner())
        agent.set_task("Test task", ["Todo 1", "Todo 2", "Todo 3"], [])

        # Create mock handlers
        action_handler = AsyncMock()
        image_provider = AsyncMock()
        image_provider.return_value = b"mock image"

        # Execute
        result = await agent.execute("Test task", action_handler, image_provider)

        assert result is True
        assert all(t.status == TodoStatus.COMPLETED for t in agent.memory.todos)
        assert len(agent.memory.history) == 3

    @patch("oagi.agent.tasker.taskee_agent.TaskeeAgent.execute")
    async def test_execute_with_failure(self, mock_execute):
        """Test execution when a todo fails."""
        # Setup mock to fail
        mock_execute.side_effect = Exception("Test error")

        # Create agent and set task
        agent = TaskerAgent(planner=MockPlanner())
        agent.set_task("Test task", ["Todo 1"], [])

        # Create mock handlers
        action_handler = AsyncMock()
        image_provider = AsyncMock()
        image_provider.return_value = b"mock image"

        # Execute
        result = await agent.execute("Test task", action_handler, image_provider)

        assert result is False
        # Todo should remain in progress after failure
        assert agent.memory.todos[0].status == TodoStatus.IN_PROGRESS

    async def test_append_todo(self):
        """Test dynamically appending a todo."""
        agent = TaskerAgent()
        agent.set_task("Test task", ["Todo 1"], [])

        agent.append_todo("Todo 2")

        assert len(agent.memory.todos) == 2
        assert agent.memory.todos[1].description == "Todo 2"
        assert agent.memory.todos[1].status == TodoStatus.PENDING

    async def test_append_deliverable(self):
        """Test dynamically appending a deliverable."""
        agent = TaskerAgent()
        agent.set_task("Test task", ["Todo 1"], ["Deliverable 1"])

        agent.append_deliverable("Deliverable 2")

        assert len(agent.memory.deliverables) == 2
        assert agent.memory.deliverables[1].description == "Deliverable 2"
        assert agent.memory.deliverables[1].achieved is False

    async def test_get_memory(self):
        """Test getting memory state."""
        agent = TaskerAgent()
        agent.set_task("Test task", ["Todo 1"], [])

        memory = agent.get_memory()

        assert memory is agent.memory
        assert memory.task_description == "Test task"
        assert len(memory.todos) == 1

    async def test_update_task_summary(self):
        """Test updating task execution summary."""
        agent = TaskerAgent()
        agent.set_task("Test task", ["Todo 1", "Todo 2"], [])

        # Mark first todo as completed
        agent.memory.update_todo(0, TodoStatus.COMPLETED, "First completed")
        agent.memory.add_history(0, [], summary="First completed", completed=True)

        agent._update_task_summary()

        assert "1/2 todos completed" in agent.memory.task_execution_summary
        assert "Todo 0: First completed" in agent.memory.task_execution_summary
