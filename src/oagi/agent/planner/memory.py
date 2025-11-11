"""Memory management for the planner agent system."""

from typing import Any

from .models import Action, Deliverable, Todo, TodoHistory, TodoStatus


class PlannerMemory:
    """In-memory state management for the planner agent."""

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

    def format_task_overview(self) -> str:
        """Format task instruction, deliverables, and todos as markdown.

        Returns:
            Markdown-formatted string with task overview
        """
        lines: list[str] = []

        lines.append("## Task Instruction")
        lines.append(self.task_description or "No instruction provided")
        lines.append("")

        lines.append("## Deliverables")
        if self.deliverables:
            for i, d in enumerate(self.deliverables):
                status = "✅" if d.achieved else "❌"
                lines.append(f"{i + 1}. {status} {d.description}")
        else:
            lines.append("No deliverables defined")
        lines.append("")

        lines.append("## Todos")
        if self.todos:
            for i, t in enumerate(self.todos):
                lines.append(f"{i + 1}. {t.description} ({t.status.value})")
        else:
            lines.append("No todos defined")
        lines.append("")

        return "\n".join(lines)

    def format_execution_summary(self, include_last_todo: bool = False) -> str:
        """Format task execution summary and optionally last todo summary.

        Args:
            include_last_todo: Whether to include the last todo's execution summary

        Returns:
            Markdown-formatted execution summary
        """
        lines: list[str] = []

        lines.append("## Task Execution Summary")
        lines.append(self.task_execution_summary or "No summary available")
        lines.append("")

        if include_last_todo and self.todo_execution_summaries:
            last_idx = max(self.todo_execution_summaries.keys())
            last_summary = self.todo_execution_summaries[last_idx]
            lines.append("## Last Todo Execution Summary")
            lines.append(last_summary)
            lines.append("")

        return "\n".join(lines)

    def format_todo_histories(self) -> str:
        """Format todo execution histories as markdown.

        Returns:
            Markdown-formatted todo histories
        """
        lines: list[str] = []

        lines.append("## Todo Histories")
        if self.history:
            for i, th in enumerate(self.history):
                lines.append(f"### Todo History {i + 1}")
                lines.append(f"Todo: {th.todo}")
                lines.append(f"Actions: {len(th.actions)}")
                lines.append(f"Completed: {th.completed}")
                if th.summary:
                    lines.append(f"Summary: {th.summary}")
                lines.append("")
        else:
            lines.append("No todo histories available")
        lines.append("")

        return "\n".join(lines)

    def format_full_context(self, include_histories: bool = False) -> str:
        """Format complete context as markdown.

        Args:
            include_histories: Whether to include full todo histories

        Returns:
            Markdown-formatted complete context
        """
        lines: list[str] = []

        # Task overview
        lines.append(self.format_task_overview())

        # Execution summary
        lines.append(self.format_execution_summary(include_last_todo=False))

        # Optionally include histories
        if include_histories:
            lines.append(self.format_todo_histories())

        return "\n".join(lines)

    def format_internal_context(self, todo_index: int) -> str:
        """Format internal context for a specific todo (for OAGI workers).

        This includes the current todo, its status, and relevant execution context.

        Args:
            todo_index: Index of the current todo

        Returns:
            Markdown-formatted internal context
        """
        lines: list[str] = []

        if 0 <= todo_index < len(self.todos):
            current_todo = self.todos[todo_index]
            lines.append(f"## Current Todo ({current_todo.status.value})")
            lines.append(current_todo.description)
            lines.append("")

            # Include execution summary if available
            if todo_index in self.todo_execution_summaries:
                lines.append("## Current Todo Progress")
                lines.append(self.todo_execution_summaries[todo_index])
                lines.append("")

        # Show all todos for context
        lines.append("## All Todos")
        for i, t in enumerate(self.todos):
            marker = "→" if i == todo_index else " "
            lines.append(f"{marker} {i + 1}. {t.description} ({t.status.value})")
        lines.append("")

        return "\n".join(lines)

    def format_external_context(self) -> str:
        """Format external context (overall task and deliverables).

        Returns:
            Markdown-formatted external context
        """
        lines: list[str] = []

        lines.append("## Overall Task")
        lines.append(self.task_description or "No task description")
        lines.append("")

        lines.append("## Deliverables")
        if self.deliverables:
            for i, d in enumerate(self.deliverables):
                status = "✅" if d.achieved else "❌"
                lines.append(f"{i + 1}. {status} {d.description}")
        else:
            lines.append("No deliverables defined")
        lines.append("")

        if self.task_execution_summary:
            lines.append("## Overall Progress")
            lines.append(self.task_execution_summary)
            lines.append("")

        return "\n".join(lines)
