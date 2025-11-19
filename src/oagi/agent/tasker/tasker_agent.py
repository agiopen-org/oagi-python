# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import logging
from typing import Any

from oagi.types import AsyncActionHandler, AsyncImageProvider, AsyncStepObserver

from ..protocol import AsyncAgent
from .memory import PlannerMemory
from .models import TodoStatus
from .planner import Planner
from .taskee_agent import TaskeeAgent

logger = logging.getLogger(__name__)


class TaskerAgent(AsyncAgent):
    """Hierarchical agent that manages multi-todo workflows.

    This agent orchestrates the execution of multiple todos by:
    1. Managing a workflow with todos and deliverables
    2. Executing todos sequentially using TaskeeAgent
    3. Tracking progress and updating memory
    4. Sharing context between todos for informed execution
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "lux-actor-1",
        max_steps: int = 60,
        temperature: float = 0.5,
        reflection_interval: int = 4,
        planner: Planner | None = None,
        step_observer: AsyncStepObserver | None = None,
    ):
        """Initialize the tasker agent.

        Args:
            api_key: OAGI API key
            base_url: OAGI API base URL
            model: Model to use for vision tasks
            max_steps: Maximum steps per todo
            temperature: Sampling temperature
            reflection_interval: Actions before reflection
            planner: Planner for planning and reflection
            step_observer: Optional observer for step tracking
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_steps = max_steps
        self.temperature = temperature
        self.reflection_interval = reflection_interval
        self.planner = planner or Planner(api_key=api_key, base_url=base_url)
        self.step_observer = step_observer

        # Memory for tracking workflow
        self.memory = PlannerMemory()

        # Current execution state
        self.current_taskee_agent: TaskeeAgent | None = None
        self.current_todo_index: int = -1

    def set_task(
        self,
        task: str,
        todos: list[str],
        deliverables: list[str] | None = None,
    ) -> None:
        """Set the task, todos, and deliverables for the workflow.

        Args:
            task: Overall task description
            todos: List of todo descriptions
            deliverables: Optional list of deliverable descriptions
        """
        self.memory.set_task(task, todos, deliverables)
        logger.info(
            f"Task set with {len(todos)} todos and "
            f"{len(deliverables) if deliverables else 0} deliverables"
        )

    async def execute(
        self,
        instruction: str,
        action_handler: AsyncActionHandler,
        image_provider: AsyncImageProvider,
    ) -> bool:
        """Execute the multi-todo workflow.

        This method will execute todos sequentially until all are complete
        or a failure occurs.

        Args:
            instruction: Overall instruction (can be same as task description)
            action_handler: Handler for executing actions
            image_provider: Provider for capturing screenshots

        Returns:
            True if all todos completed successfully, False otherwise
        """
        # If task not set, use instruction as task description
        if not self.memory.task_description:
            logger.warning("Task not set, using instruction as task description")
            self.memory.task_description = instruction

        overall_success = True

        # Execute todos until none remain
        while True:
            # Prepare for next todo
            todo_info = self._prepare()

            if todo_info is None:
                # No more todos to execute
                logger.info("No more todos to execute")
                break

            todo, todo_index = todo_info
            logger.info(f"Executing todo {todo_index}: {todo.description}")

            # Execute the todo
            success = await self._execute_todo(
                todo_index,
                action_handler,
                image_provider,
            )

            if not success:
                logger.warning(f"Todo {todo_index} failed")
                overall_success = False
                # If todo failed due to exception, it stays IN_PROGRESS
                # Break to avoid infinite loop re-attempting same todo
                current_status = self.memory.todos[todo_index].status
                if current_status == TodoStatus.IN_PROGRESS:
                    logger.error("Todo failed with exception, stopping execution")
                    break
                # Otherwise continue with next todo

            # Update task execution summary
            self._update_task_summary()

        # Log final status
        status_summary = self.memory.get_todo_status_summary()
        logger.info(f"Workflow complete. Status summary: {status_summary}")

        return overall_success

    def _prepare(self) -> tuple[Any, int] | None:
        """Prepare for the next todo execution.

        Returns:
            Tuple of (todo, index) or None if no todos remain
        """
        # Get current todo
        todo, todo_index = self.memory.get_current_todo()

        if todo is None:
            return None

        # Create taskee agent with external memory
        self.current_taskee_agent = TaskeeAgent(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_steps_per_subtask=20,  # Smaller steps per subtask
            reflection_interval=self.reflection_interval,
            temperature=self.temperature,
            planner=self.planner,
            external_memory=self.memory,  # Share memory with child
            todo_index=todo_index,  # Pass the todo index
            step_observer=self.step_observer,  # Pass step observer
        )

        self.current_todo_index = todo_index

        # Update todo status to in_progress if it was pending
        if todo.status == TodoStatus.PENDING:
            self.memory.update_todo(todo_index, TodoStatus.IN_PROGRESS)

        logger.info(f"Prepared taskee agent for todo {todo_index}")

        return todo, todo_index

    async def _execute_todo(
        self,
        todo_index: int,
        action_handler: AsyncActionHandler,
        image_provider: AsyncImageProvider,
    ) -> bool:
        """Execute a single todo using the todo agent.

        Args:
            todo_index: Index of the todo to execute
            action_handler: Handler for executing actions
            image_provider: Provider for capturing screenshots

        Returns:
            True if successful, False otherwise
        """
        if not self.current_taskee_agent or todo_index < 0:
            logger.error("No taskee agent prepared")
            return False

        todo = self.memory.todos[todo_index]

        try:
            # Execute using taskee agent
            success = await self.current_taskee_agent.execute(
                todo.description,
                action_handler,
                image_provider,
            )

            # Get execution results
            results = self.current_taskee_agent.return_execution_results()

            # Update memory with results
            self._update_memory_from_execution(todo_index, results, success)

            return success

        except Exception as e:
            logger.error(f"Error executing todo {todo_index}: {e}")
            # Mark as in_progress (not completed)
            self.memory.update_todo(
                todo_index,
                TodoStatus.IN_PROGRESS,
                summary=f"Execution failed: {str(e)}",
            )
            return False

    def _update_memory_from_execution(
        self,
        todo_index: int,
        results: Any,
        success: bool,
    ) -> None:
        """Update memory based on execution results.

        Args:
            todo_index: Index of the executed todo
            results: Execution results from todo agent
            success: Whether execution was successful
        """
        # Update todo status
        status = TodoStatus.COMPLETED if success else TodoStatus.IN_PROGRESS
        self.memory.update_todo(
            todo_index,
            status,
            summary=results.summary,
        )

        # Add to history
        self.memory.add_history(
            todo_index,
            results.actions,
            summary=results.summary,
            completed=success,
        )

        # Update task execution summary
        if success:
            if self.memory.task_execution_summary:
                self.memory.task_execution_summary += (
                    f"\n- Completed todo {todo_index}: {results.summary}"
                )
            else:
                self.memory.task_execution_summary = (
                    f"- Completed todo {todo_index}: {results.summary}"
                )

        logger.info(
            f"Updated memory for todo {todo_index}: "
            f"status={status}, actions={len(results.actions)}"
        )

    def _update_task_summary(self) -> None:
        """Update the overall task execution summary."""
        status_summary = self.memory.get_todo_status_summary()
        completed = status_summary.get(TodoStatus.COMPLETED, 0)
        total = len(self.memory.todos)

        summary_parts = [f"Progress: {completed}/{total} todos completed"]

        # Add recent completions
        for history in self.memory.history[-3:]:  # Last 3 entries
            if history.completed and history.summary:
                summary_parts.append(
                    f"- Todo {history.todo_index}: {history.summary[:100]}"
                )

        self.memory.task_execution_summary = "\n".join(summary_parts)

    def get_memory(self) -> PlannerMemory:
        """Get the current memory state.

        Returns:
            Current PlannerMemory instance
        """
        return self.memory

    def append_todo(self, description: str) -> None:
        """Dynamically append a new todo to the workflow.

        Args:
            description: Description of the new todo
        """
        self.memory.append_todo(description)
        logger.info(f"Appended new todo: {description}")

    def append_deliverable(self, description: str) -> None:
        """Dynamically append a new deliverable to the workflow.

        Args:
            description: Description of the new deliverable
        """
        self.memory.append_deliverable(description)
        logger.info(f"Appended new deliverable: {description}")
