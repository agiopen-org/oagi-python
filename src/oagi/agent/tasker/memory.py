# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Any

from .models import Action, Deliverable, Todo, TodoHistory, TodoStatus


class PlannerMemory:
    """In-memory state management for the planner agent.

    This class manages the hierarchical task execution state for TaskerAgent.
    It provides methods for:
    - Task/todo/deliverable management
    - Execution history tracking
    - Memory state serialization

    Context formatting for backend API calls is handled by the backend.
    """

    def __init__(self):
        """Initialize empty memory."""
        self.task_description: str = ""
        self.todos: list[Todo] = []
        self.deliverables: list[Deliverable] = []
        self.history: list[TodoHistory] = []
        self.task_execution_summary: str = ""
        self.todo_execution_summaries: dict[int, str] = {}

    def set_task(
        self,
        task_description: str,
        todos: list[str] | list[Todo],
        deliverables: list[str] | list[Deliverable] | None = None,
    ) -> None:
        """Set the task, todos, and deliverables.

        Args:
            task_description: Overall task description
            todos: List of todo items (strings or Todo objects)
            deliverables: Optional list of deliverables (strings or Deliverable objects)
        """
        self.task_description = task_description

        # Convert todos
        self.todos = []
        for todo in todos:
            if isinstance(todo, str):
                self.todos.append(Todo(description=todo))
            else:
                self.todos.append(todo)

        # Convert deliverables
        self.deliverables = []
        if deliverables:
            for deliverable in deliverables:
                if isinstance(deliverable, str):
                    self.deliverables.append(Deliverable(description=deliverable))
                else:
                    self.deliverables.append(deliverable)

    def get_current_todo(self) -> tuple[Todo | None, int]:
        """Get the next pending or in-progress todo.

        Returns:
            Tuple of (Todo object, index) or (None, -1) if no todos remain
        """
        for idx, todo in enumerate(self.todos):
            if todo.status in [TodoStatus.PENDING, TodoStatus.IN_PROGRESS]:
                return todo, idx
        return None, -1

    def update_todo(
        self,
        index: int,
        status: TodoStatus | str,
        summary: str | None = None,
    ) -> None:
        """Update a todo's status and optionally its summary.

        Args:
            index: Index of the todo to update
            status: New status for the todo
            summary: Optional execution summary
        """
        if 0 <= index < len(self.todos):
            if isinstance(status, str):
                status = TodoStatus(status)
            self.todos[index].status = status
            if summary:
                self.todo_execution_summaries[index] = summary

    def add_history(
        self,
        todo_index: int,
        actions: list[Action],
        summary: str | None = None,
        completed: bool = False,
    ) -> None:
        """Add execution history for a todo.

        Args:
            todo_index: Index of the todo
            actions: List of actions taken
            summary: Optional execution summary
            completed: Whether the todo was completed
        """
        if 0 <= todo_index < len(self.todos):
            self.history.append(
                TodoHistory(
                    todo_index=todo_index,
                    todo=self.todos[todo_index].description,
                    actions=actions,
                    summary=summary,
                    completed=completed,
                )
            )

    def get_context(self) -> dict[str, Any]:
        """Get the full context for planning/reflection.

        Returns:
            Dictionary containing all memory state
        """
        return {
            "task_description": self.task_description,
            "todos": [
                {"index": i, "description": t.description, "status": t.status}
                for i, t in enumerate(self.todos)
            ],
            "deliverables": [
                {"description": d.description, "achieved": d.achieved}
                for d in self.deliverables
            ],
            "history": [
                {
                    "todo_index": h.todo_index,
                    "todo": h.todo,
                    "action_count": len(h.actions),
                    "summary": h.summary,
                    "completed": h.completed,
                }
                for h in self.history
            ],
            "task_execution_summary": self.task_execution_summary,
            "todo_execution_summaries": self.todo_execution_summaries,
        }

    def get_todo_status_summary(self) -> dict[str, int]:
        """Get a summary of todo statuses.

        Returns:
            Dictionary with counts for each status
        """
        summary = {
            TodoStatus.PENDING: 0,
            TodoStatus.IN_PROGRESS: 0,
            TodoStatus.COMPLETED: 0,
            TodoStatus.SKIPPED: 0,
        }
        for todo in self.todos:
            summary[todo.status] += 1
        return summary

    def append_todo(self, description: str) -> None:
        """Append a new todo to the list.

        Args:
            description: Description of the new todo
        """
        self.todos.append(Todo(description=description))

    def append_deliverable(self, description: str) -> None:
        """Append a new deliverable to the list.

        Args:
            description: Description of the new deliverable
        """
        self.deliverables.append(Deliverable(description=description))
