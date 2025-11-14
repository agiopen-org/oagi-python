"""Tests for the TaskeeAgent."""

from unittest.mock import AsyncMock, patch

import pytest

from oagi.agent.tasker.memory import PlannerMemory
from oagi.agent.tasker.planner import Planner
from oagi.agent.tasker.taskee_agent import TaskeeAgent
from oagi.types.models import Action as OAGIAction
from oagi.types.models import ActionType, Step
from oagi.types.models.client import GenerateResponse, UploadFileResponse


class MockPlanner(Planner):
    """Mock planner for testing."""

    def __init__(self):
        # Create a mock client instead of a real one
        mock_client = AsyncMock()

        # Track which worker is being called and return appropriate responses
        def call_worker_side_effect(*args, **kwargs):
            worker_id = kwargs.get("worker_id")
            if worker_id == "oagi_first":
                # Initial planning response
                return GenerateResponse(
                    response='{"reasoning": "Need to submit form", "subtask": "Click the submit button"}',
                    prompt_tokens=100,
                    completion_tokens=50,
                    cost=0.001,
                )
            elif worker_id == "oagi_follow":
                # Reflection response (continue with current approach)
                return GenerateResponse(
                    response='{"success": "no", "subtask_instruction": "", "reflection": "Making progress"}',
                    prompt_tokens=100,
                    completion_tokens=50,
                    cost=0.001,
                )
            else:
                # Summary response
                return GenerateResponse(
                    response='{"task_summary": "Successfully submitted the form"}',
                    prompt_tokens=80,
                    completion_tokens=20,
                    cost=0.001,
                )

        mock_client.call_worker = AsyncMock(side_effect=call_worker_side_effect)
        mock_client.put_s3_presigned_url = AsyncMock(
            return_value=UploadFileResponse(
                url="https://mock-s3.example.com/upload",
                uuid="mock-uuid-123",
                expires_at=1234567890,
                file_expires_at=1234567890,
                download_url="https://mock-s3.example.com/image.jpg",
            )
        )
        super().__init__(client=mock_client)

    async def _call_external_llm(self, prompt: str, image: bytes | None = None) -> str:
        """Mock LLM call that returns canned responses."""
        if "initial plan" in prompt.lower():
            return '{"instruction": "Click the submit button", "reasoning": "Need to submit form", "subtodos": []}'
        elif "reflect" in prompt.lower():
            return '{"continue_current": true, "new_instruction": null, "reasoning": "Making progress", "success_assessment": false}'
        else:
            return "Successfully submitted the form"


@pytest.mark.asyncio
class TestTaskeeAgent:
    """Test suite for TaskeeAgent."""

    async def test_init(self):
        """Test TaskeeAgent initialization."""
        external_memory = PlannerMemory()
        planner = MockPlanner()

        agent = TaskeeAgent(
            api_key="test-key",
            base_url="https://api.test.com",
            model="test-model",
            max_steps_per_subtask=15,
            reflection_interval=25,
            temperature=0.7,
            planner=planner,
            external_memory=external_memory,
        )

        assert agent.api_key == "test-key"
        assert agent.base_url == "https://api.test.com"
        assert agent.model == "test-model"
        assert agent.max_steps_per_subtask == 15
        assert agent.reflection_interval == 25
        assert agent.temperature == 0.7
        assert agent.planner is planner
        assert agent.external_memory is external_memory
        assert agent.actor is None
        assert agent.actions == []

    @patch("oagi.agent.tasker.taskee_agent.AsyncActor")
    async def test_initial_plan(self, mock_async_actor):
        """Test initial planning phase."""
        agent = TaskeeAgent(planner=MockPlanner())

        # Mock image provider
        image_provider = AsyncMock()
        image_provider.return_value = b"test image"

        # Execute initial plan
        await agent._initial_plan(image_provider)

        # Check that instruction was set
        assert agent.current_instruction == "Click the submit button"
        assert len(agent.actions) == 1
        assert agent.actions[0].action_type == "plan"
        assert agent.actions[0].target == "initial"

    @patch("oagi.agent.tasker.taskee_agent.AsyncActor")
    async def test_execute_subtask_success(self, mock_async_actor_class):
        """Test executing a subtask successfully."""
        # Setup mock actor
        mock_actor = AsyncMock()
        # Configure async context manager
        mock_async_actor_class.return_value.__aenter__.return_value = mock_actor

        # Mock step response
        mock_step = Step(
            reasoning="Found button",
            actions=[
                OAGIAction(
                    type=ActionType.CLICK,
                    argument="100,200",
                )
            ],
            stop=True,  # Signal completion
        )
        mock_actor.step.return_value = mock_step

        agent = TaskeeAgent(planner=MockPlanner())
        agent.current_instruction = "Click submit"

        # Mock handlers
        action_handler = AsyncMock()
        image_provider = AsyncMock()
        image_provider.return_value = b"test image"

        # Execute subtask
        steps_taken = await agent._execute_subtask(
            max_steps=10,
            action_handler=action_handler,
            image_provider=image_provider,
        )

        assert steps_taken == 1
        assert agent.success is True
        assert len(agent.actions) == 1
        assert agent.actions[0].action_type == "click"
        mock_actor.init_task.assert_called_once_with("Click submit")
        # close() is now handled automatically by async with context manager
        action_handler.assert_called_once()

    @patch("oagi.agent.tasker.taskee_agent.AsyncActor")
    async def test_execute_subtask_with_reflection_trigger(
        self, mock_async_actor_class
    ):
        """Test that reflection is triggered at interval."""
        # Setup mock actor
        mock_actor = AsyncMock()
        # Configure async context manager
        mock_async_actor_class.return_value.__aenter__.return_value = mock_actor

        # Mock step responses (many actions to trigger reflection)
        mock_step = Step(
            reasoning="Action",
            actions=[OAGIAction(type=ActionType.CLICK, argument="100,200")],
            stop=False,
        )
        mock_actor.step.return_value = mock_step

        agent = TaskeeAgent(planner=MockPlanner(), reflection_interval=3)
        agent.current_instruction = "Test instruction"

        # Mock handlers
        action_handler = AsyncMock()
        image_provider = AsyncMock()
        image_provider.return_value = b"test image"

        # Execute subtask - should stop after 3 actions due to reflection
        steps_taken = await agent._execute_subtask(
            max_steps=10,
            action_handler=action_handler,
            image_provider=image_provider,
        )

        assert steps_taken == 3  # Stopped at reflection interval
        assert agent.since_reflection == 3
        assert agent.total_actions == 3

    async def test_reflect_and_decide_continue(self):
        """Test reflection that decides to continue."""
        agent = TaskeeAgent(planner=MockPlanner())
        agent.current_todo = "Test todo"
        agent.since_reflection = 5
        agent.actions = [
            agent._record_action("click", "button", "test") or agent.actions[-1]
            for _ in range(5)
        ]

        # Mock image provider
        image_provider = AsyncMock()
        image_provider.return_value = b"test image"

        # Reflect
        should_continue = await agent._reflect_and_decide(image_provider)

        assert should_continue is True
        assert agent.since_reflection == 0  # Reset after reflection
        assert agent.success is False
        assert any(a.action_type == "reflect" for a in agent.actions)

    async def test_reflect_and_decide_pivot(self):
        """Test reflection that decides to pivot with new instruction."""

        class PivotPlanner(Planner):
            def __init__(self):
                mock_client = AsyncMock()
                mock_client.call_worker = AsyncMock(
                    return_value=GenerateResponse(
                        response='{"success": "no", "subtask_instruction": "Try different approach", "reflection": "Not working"}',
                        prompt_tokens=100,
                        completion_tokens=50,
                        cost=0.001,
                    )
                )
                mock_client.put_s3_presigned_url = AsyncMock(
                    return_value=UploadFileResponse(
                        url="https://mock-s3.example.com/upload",
                        uuid="mock-uuid-test",
                        expires_at=1234567890,
                        file_expires_at=1234567890,
                        download_url="https://mock-s3.example.com/image.jpg",
                    )
                )
                super().__init__(client=mock_client)

            async def _call_external_llm(
                self, prompt: str, image: bytes | None = None
            ) -> str:
                return '{"continue_current": false, "new_instruction": "Try different approach", "reasoning": "Not working", "success_assessment": false}'

        agent = TaskeeAgent(planner=PivotPlanner())
        agent.current_todo = "Test todo"
        agent.current_instruction = "Original instruction"

        # Mock image provider
        image_provider = AsyncMock()
        image_provider.return_value = b"test image"

        # Reflect
        should_continue = await agent._reflect_and_decide(image_provider)

        assert should_continue is True
        assert agent.current_instruction == "Try different approach"

    async def test_reflect_success_assessment(self):
        """Test reflection that assesses success."""

        class SuccessPlanner(Planner):
            def __init__(self):
                mock_client = AsyncMock()
                mock_client.call_worker = AsyncMock(
                    return_value=GenerateResponse(
                        response='{"success": "yes", "subtask_instruction": "", "reflection": "Task completed"}',
                        prompt_tokens=100,
                        completion_tokens=50,
                        cost=0.001,
                    )
                )
                mock_client.put_s3_presigned_url = AsyncMock(
                    return_value=UploadFileResponse(
                        url="https://mock-s3.example.com/upload",
                        uuid="mock-uuid-test",
                        expires_at=1234567890,
                        file_expires_at=1234567890,
                        download_url="https://mock-s3.example.com/image.jpg",
                    )
                )
                super().__init__(client=mock_client)

            async def _call_external_llm(
                self, prompt: str, image: bytes | None = None
            ) -> str:
                return '{"continue_current": false, "new_instruction": null, "reasoning": "Task completed", "success_assessment": true}'

        agent = TaskeeAgent(planner=SuccessPlanner())
        agent.current_todo = "Test todo"

        # Mock image provider
        image_provider = AsyncMock()
        image_provider.return_value = b"test image"

        # Reflect
        should_continue = await agent._reflect_and_decide(image_provider)

        assert should_continue is False
        assert agent.success is True

    @patch("oagi.agent.tasker.taskee_agent.TaskeeAgent._initial_plan")
    @patch("oagi.agent.tasker.taskee_agent.TaskeeAgent._execute_subtask")
    @patch("oagi.agent.tasker.taskee_agent.TaskeeAgent._reflect_and_decide")
    @patch("oagi.agent.tasker.taskee_agent.TaskeeAgent._generate_summary")
    async def test_execute_full_flow(
        self,
        mock_generate_summary,
        mock_reflect,
        mock_execute_subtask,
        mock_initial_plan,
    ):
        """Test full execution flow."""
        # Setup mocks
        mock_execute_subtask.side_effect = [5, 5]  # Two subtask executions
        mock_reflect.side_effect = [True, False]  # Continue once, then stop

        agent = TaskeeAgent(planner=MockPlanner())

        # Mock handlers
        action_handler = AsyncMock()
        image_provider = AsyncMock()

        # Execute
        await agent.execute("Test todo", action_handler, image_provider)

        # Verify flow
        mock_initial_plan.assert_called_once()
        assert mock_execute_subtask.call_count == 2
        assert mock_reflect.call_count == 2
        mock_generate_summary.assert_called_once()

    async def test_execute_with_error(self):
        """Test execution with error handling."""
        agent = TaskeeAgent(planner=MockPlanner())

        # Mock handlers that raise error
        action_handler = AsyncMock()
        image_provider = AsyncMock()
        image_provider.side_effect = Exception("Image capture failed")

        # Execute
        result = await agent.execute("Test todo", action_handler, image_provider)

        assert result is False
        assert any(
            a.action_type == "error" and "Image capture failed" in (a.reasoning or "")
            for a in agent.actions
        )

    async def test_return_execution_results(self):
        """Test returning execution results."""
        agent = TaskeeAgent()
        agent.success = True
        agent.total_actions = 10

        # Add some actions including a summary
        agent._record_action("click", "button", "test")
        agent._record_action("type", "input", "test")
        agent._record_action("summary", None, "Task completed successfully")

        results = agent.return_execution_results()

        assert results.success is True
        assert results.total_steps == 10
        assert results.summary == "Task completed successfully"
        assert len(results.actions) == 3

    async def test_get_context_with_external_memory(self):
        """Test getting context with external memory."""
        memory = PlannerMemory()
        memory.set_task("Main task", ["Todo 1", "Todo 2"])

        agent = TaskeeAgent(external_memory=memory)

        context = agent._get_context()

        assert context["task_description"] == "Main task"
        assert len(context["todos"]) == 2

    async def test_get_context_without_external_memory(self):
        """Test getting context without external memory."""
        agent = TaskeeAgent()

        context = agent._get_context()

        assert context == {}
