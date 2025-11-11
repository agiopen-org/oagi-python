"""Single todo executor with planning and reflection capabilities."""

import logging
from datetime import datetime
from typing import Any

from oagi import AsyncTask
from oagi.types import AsyncActionHandler, AsyncImageProvider

from ..protocol import AsyncAgent
from .llm_planner import LLMPlanner
from .memory import PlannerMemory
from .models import Action, ExecutionResult

logger = logging.getLogger(__name__)


class TodoAgent(AsyncAgent):
    """Executes a single todo with planning and reflection capabilities.

    This agent uses an LLM planner to:
    1. Convert a todo into a clear actionable instruction
    2. Execute the instruction using OAGI API
    3. Periodically reflect on progress and adjust approach
    4. Generate execution summaries
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-v1",
        max_steps_per_subtask: int = 10,
        reflection_interval: int = 20,
        temperature: float = 0.0,
        planner: LLMPlanner | None = None,
        external_memory: PlannerMemory | None = None,
        todo_index: int | None = None,
    ):
        """Initialize the todo agent.

        Args:
            api_key: OAGI API key
            base_url: OAGI API base URL
            model: Model to use for vision tasks
            max_steps_per_subtask: Maximum steps before reinitializing task
            reflection_interval: Number of actions before triggering reflection
            temperature: Sampling temperature
            planner: LLM planner for planning and reflection
            external_memory: External memory from parent agent
            todo_index: Index of the todo being executed
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_steps_per_subtask = max_steps_per_subtask
        self.reflection_interval = reflection_interval
        self.temperature = temperature
        self.planner = planner or LLMPlanner()
        self.external_memory = external_memory
        self.todo_index = todo_index

        # Internal state
        self.task: AsyncTask | None = None
        self.current_todo: str = ""
        self.current_instruction: str = ""
        self.actions: list[Action] = []
        self.total_actions = 0
        self.since_reflection = 0
        self.success = False

    async def execute(
        self,
        instruction: str,
        action_handler: AsyncActionHandler,
        image_provider: AsyncImageProvider,
    ) -> bool:
        """Execute the todo using planning and reflection.

        Args:
            instruction: The todo description to execute
            action_handler: Handler for executing actions
            image_provider: Provider for capturing screenshots

        Returns:
            True if successful, False otherwise
        """
        self.current_todo = instruction
        self.actions = []
        self.total_actions = 0
        self.since_reflection = 0
        self.success = False

        try:
            # Initial planning
            await self._initial_plan(image_provider)

            # Main execution loop with reinitializations
            max_total_steps = self.max_steps_per_subtask * 3  # Allow up to 3 reinits
            remaining_steps = max_total_steps

            while remaining_steps > 0 and not self.success:
                # Execute subtask
                steps_taken = await self._execute_subtask(
                    min(self.max_steps_per_subtask, remaining_steps),
                    action_handler,
                    image_provider,
                )
                remaining_steps -= steps_taken

                # Check if we should continue
                if not self.success and remaining_steps > 0:
                    # Reflect and potentially get new instruction
                    should_continue = await self._reflect_and_decide(image_provider)
                    if not should_continue:
                        break

            # Generate final summary
            await self._generate_summary()

            return self.success

        except Exception as e:
            logger.error(f"Error executing todo: {e}")
            self._record_action(
                action_type="error",
                target=None,
                reasoning=str(e),
            )
            return False
        finally:
            # Clean up task
            if self.task:
                await self.task.close()
                self.task = None

    async def _initial_plan(self, image_provider: AsyncImageProvider) -> None:
        """Generate initial plan for the todo.

        Args:
            image_provider: Provider for capturing screenshots
        """
        logger.info("Generating initial plan for todo")

        # Capture initial screenshot
        screenshot = await image_provider()

        # Get context from external memory if available
        context = self._get_context()

        # Generate plan using LLM planner
        plan_output = await self.planner.initial_plan(
            self.current_todo,
            context,
            screenshot,
            memory=self.external_memory,
            todo_index=self.todo_index,
        )

        # Record planning action
        self._record_action(
            action_type="plan",
            target="initial",
            reasoning=plan_output.reasoning,
            result=plan_output.instruction,
        )

        # Set current instruction
        self.current_instruction = plan_output.instruction
        logger.info(f"Initial instruction: {self.current_instruction}")

        # Handle subtodos if any
        if plan_output.subtodos:
            logger.info(f"Planner created {len(plan_output.subtodos)} subtodos")
            # Could potentially add these to memory for tracking

    async def _execute_subtask(
        self,
        max_steps: int,
        action_handler: AsyncActionHandler,
        image_provider: AsyncImageProvider,
    ) -> int:
        """Execute a subtask with the current instruction.

        Args:
            max_steps: Maximum steps for this subtask
            action_handler: Handler for executing actions
            image_provider: Provider for capturing screenshots

        Returns:
            Number of steps taken
        """
        logger.info(f"Executing subtask with max {max_steps} steps")

        # Use async with for automatic resource management
        async with AsyncTask(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature,
        ) as task:
            # Store reference for potential cleanup in execute's finally block
            self.task = task

            # Initialize task with current instruction
            await task.init_task(self.current_instruction)

            steps_taken = 0
            for step_num in range(max_steps):
                # Capture screenshot
                screenshot = await image_provider()

                # Get next step from OAGI
                try:
                    step = await task.step(screenshot, instruction=None)
                except Exception as e:
                    logger.error(f"Error getting step from OAGI: {e}")
                    self._record_action(
                        action_type="error",
                        target="oagi_step",
                        reasoning=str(e),
                    )
                    break

                # Record OAGI actions
                if step.actions:
                    for action in step.actions:
                        self._record_action(
                            action_type=action.type.lower(),
                            target=action.argument,
                            reasoning=step.reason,
                        )

                    # Execute actions
                    await action_handler(step.actions)
                    self.total_actions += len(step.actions)
                    self.since_reflection += len(step.actions)

                steps_taken += 1

                # Check if task is complete
                if step.stop:
                    logger.info("OAGI signaled task completion")
                    self.success = True
                    break

                # Check if reflection is needed
                if self.since_reflection >= self.reflection_interval:
                    logger.info("Reflection interval reached")
                    break

            # Task will be automatically closed by async with context manager
            # Clear reference after context manager closes it
            self.task = None
            return steps_taken

    async def _reflect_and_decide(self, image_provider: AsyncImageProvider) -> bool:
        """Reflect on progress and decide whether to continue.

        Args:
            image_provider: Provider for capturing screenshots

        Returns:
            True to continue, False to stop
        """
        logger.info("Reflecting on progress")

        # Capture current screenshot
        screenshot = await image_provider()

        # Get context
        context = self._get_context()
        context["current_todo"] = self.current_todo

        # Get recent actions for reflection
        recent_actions = self.actions[-self.since_reflection :]

        # Reflect using planner
        reflection = await self.planner.reflect(
            recent_actions,
            context,
            screenshot,
            memory=self.external_memory,
            todo_index=self.todo_index,
            current_instruction=self.current_instruction,
        )

        # Record reflection
        self._record_action(
            action_type="reflect",
            target=None,
            reasoning=reflection.reasoning,
            result=("continue" if reflection.continue_current else "pivot"),
        )

        # Update success assessment
        if reflection.success_assessment:
            self.success = True
            logger.info("Reflection indicates task is successful")
            return False

        # Reset reflection counter
        self.since_reflection = 0

        # Update instruction if needed
        if not reflection.continue_current and reflection.new_instruction:
            logger.info(f"Pivoting to new instruction: {reflection.new_instruction}")
            self.current_instruction = reflection.new_instruction
            return True

        return reflection.continue_current

    async def _generate_summary(self) -> None:
        """Generate execution summary."""
        logger.info("Generating execution summary")

        context = self._get_context()
        context["current_todo"] = self.current_todo

        summary = await self.planner.summarize(
            self.actions,
            context,
            memory=self.external_memory,
            todo_index=self.todo_index,
        )

        # Record summary
        self._record_action(
            action_type="summary",
            target=None,
            reasoning=summary,
        )

        logger.info(f"Execution summary: {summary}")

    def _record_action(
        self,
        action_type: str,
        target: str | None,
        reasoning: str | None = None,
        result: str | None = None,
    ) -> None:
        """Record an action to the history.

        Args:
            action_type: Type of action
            target: Target of the action
            reasoning: Reasoning for the action
            result: Result of the action
        """
        action = Action(
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            target=target,
            reasoning=reasoning,
            result=result,
            details={},
        )
        self.actions.append(action)

    def _get_context(self) -> dict[str, Any]:
        """Get execution context.

        Returns:
            Dictionary with context information
        """
        if self.external_memory:
            return self.external_memory.get_context()
        return {}

    def return_execution_results(self) -> ExecutionResult:
        """Return the execution results.

        Returns:
            ExecutionResult with success status, actions, and summary
        """
        # Find summary in actions
        summary = ""
        for action in reversed(self.actions):
            if action.action_type == "summary":
                summary = action.reasoning or ""
                break

        return ExecutionResult(
            success=self.success,
            actions=self.actions,
            summary=summary,
            total_steps=self.total_actions,
        )
