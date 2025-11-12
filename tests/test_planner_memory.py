"""Tests for PlannerMemory class."""

import pytest

from oagi.agent.tasker.memory import PlannerMemory
from oagi.agent.tasker.models import (
    Action,
    Deliverable,
    Todo,
    TodoStatus,
)


class TestPlannerMemory:
    @pytest.fixture
    def memory(self):
        return PlannerMemory()

    @pytest.fixture
    def populated_memory(self):
        memory = PlannerMemory()
        memory.set_task(
            task_description="Complete a test task",
            todos=["First todo", "Second todo", "Third todo"],
            deliverables=["Working system", "Documentation"],
        )
        return memory

    def test_init_empty(self, memory):
        assert memory.task_description == ""
        assert memory.todos == []
        assert memory.deliverables == []
        assert memory.history == []

    def test_set_task_with_strings(self, memory):
        memory.set_task(
            task_description="Test task",
            todos=["Todo 1", "Todo 2"],
            deliverables=["Deliverable 1"],
        )
        assert memory.task_description == "Test task"
        assert len(memory.todos) == 2
        assert all(isinstance(t, Todo) for t in memory.todos)
        assert memory.todos[0].description == "Todo 1"
        assert memory.todos[0].status == TodoStatus.PENDING

    def test_set_task_with_objects(self, memory):
        todos = [Todo(description="Todo 1"), Todo(description="Todo 2")]
        deliverables = [Deliverable(description="Deliverable 1")]
        memory.set_task(
            task_description="Test task",
            todos=todos,
            deliverables=deliverables,
        )
        assert memory.todos == todos
        assert memory.deliverables == deliverables

    def test_get_current_todo(self, populated_memory):
        todo, idx = populated_memory.get_current_todo()
        assert todo.description == "First todo"
        assert idx == 0

        # Mark first as completed
        populated_memory.update_todo(0, TodoStatus.COMPLETED)
        todo, idx = populated_memory.get_current_todo()
        assert todo.description == "Second todo"
        assert idx == 1

    def test_get_current_todo_none_remaining(self, populated_memory):
        for i in range(3):
            populated_memory.update_todo(i, TodoStatus.COMPLETED)
        todo, idx = populated_memory.get_current_todo()
        assert todo is None
        assert idx == -1

    def test_update_todo(self, populated_memory):
        populated_memory.update_todo(0, TodoStatus.IN_PROGRESS, "Working on it")
        assert populated_memory.todos[0].status == TodoStatus.IN_PROGRESS
        assert populated_memory.todo_execution_summaries[0] == "Working on it"

    def test_add_history(self, populated_memory):
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
        populated_memory.add_history(0, actions, "Clicked and typed", True)
        assert len(populated_memory.history) == 1
        history = populated_memory.history[0]
        assert history.todo_index == 0
        assert history.todo == "First todo"
        assert len(history.actions) == 2
        assert history.completed is True

    def test_get_todo_status_summary(self, populated_memory):
        populated_memory.update_todo(0, TodoStatus.COMPLETED)
        populated_memory.update_todo(1, TodoStatus.IN_PROGRESS)
        summary = populated_memory.get_todo_status_summary()
        assert summary[TodoStatus.COMPLETED] == 1
        assert summary[TodoStatus.IN_PROGRESS] == 1
        assert summary[TodoStatus.PENDING] == 1
        assert summary[TodoStatus.SKIPPED] == 0

    def test_append_todo(self, memory):
        memory.append_todo("New todo")
        assert len(memory.todos) == 1
        assert memory.todos[0].description == "New todo"

    def test_append_deliverable(self, memory):
        memory.append_deliverable("New deliverable")
        assert len(memory.deliverables) == 1
        assert memory.deliverables[0].description == "New deliverable"

    def test_get_context(self, populated_memory):
        context = populated_memory.get_context()
        assert context["task_description"] == "Complete a test task"
        assert len(context["todos"]) == 3
        assert len(context["deliverables"]) == 2
        assert context["todos"][0]["status"] == TodoStatus.PENDING


@pytest.mark.parametrize(
    "status,expected",
    [
        ("pending", TodoStatus.PENDING),
        ("in_progress", TodoStatus.IN_PROGRESS),
        ("completed", TodoStatus.COMPLETED),
        ("skipped", TodoStatus.SKIPPED),
    ],
)
def test_update_todo_with_string_status(status, expected):
    memory = PlannerMemory()
    memory.append_todo("Test todo")
    memory.update_todo(0, status)
    assert memory.todos[0].status == expected
