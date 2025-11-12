# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TodoStatus(str, Enum):
    """Status of a todo item in the workflow."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class Todo(BaseModel):
    """A single todo item in the workflow."""

    description: str
    status: TodoStatus = TodoStatus.PENDING


class Deliverable(BaseModel):
    """A deliverable or goal to be achieved."""

    description: str
    achieved: bool = False


class Action(BaseModel):
    """An action taken during execution."""

    timestamp: str
    action_type: str  # "plan", "reflect", "click", "type", "scroll", etc.
    target: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    reasoning: str | None = None
    result: str | None = None


class TodoHistory(BaseModel):
    """Execution history for a specific todo."""

    todo_index: int
    todo: str
    actions: list[Action]
    summary: str | None = None
    completed: bool = False


class PlannerOutput(BaseModel):
    """Output from the LLM planner's initial planning."""

    instruction: str  # Clear instruction for the todo
    reasoning: str  # Planner's reasoning
    subtodos: list[str] = Field(default_factory=list)  # Optional subtasks


class ReflectionOutput(BaseModel):
    """Output from the LLM planner's reflection."""

    continue_current: bool  # Whether to continue with current approach
    new_instruction: str | None = None  # New instruction if pivoting
    reasoning: str  # Reflection reasoning
    success_assessment: bool = False  # Whether the task appears successful


class ExecutionResult(BaseModel):
    """Result from executing a single todo."""

    success: bool
    actions: list[Action]
    summary: str
    error: str | None = None
    total_steps: int = 0
