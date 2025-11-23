# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from .models import Action, Step


class BaseEvent(BaseModel):
    """Base class for all observer events with automatic timestamp."""

    timestamp: datetime = Field(default_factory=datetime.now)


class ImageEvent(BaseEvent):
    """Event emitted when a screenshot is captured."""

    type: Literal["image"] = "image"
    step_num: int
    image: bytes | str


class StepEvent(BaseEvent):
    """Event emitted when LLM returns a step decision."""

    type: Literal["step"] = "step"
    step_num: int
    image: bytes | str
    step: Step


class ActionEvent(BaseEvent):
    """Event emitted after actions are executed."""

    type: Literal["action"] = "action"
    step_num: int
    actions: list[Action]
    error: str | None = None


class LogEvent(BaseEvent):
    """Event for custom log messages."""

    type: Literal["log"] = "log"
    message: str


class SplitEvent(BaseEvent):
    """Event for visual separators in exported reports."""

    type: Literal["split"] = "split"
    label: str = ""


class PlanEvent(BaseEvent):
    """Event emitted for planner activities (planning, reflection, summary)."""

    type: Literal["plan"] = "plan"
    phase: Literal["initial", "reflection", "summary"]
    image: bytes | str | None = None
    reasoning: str
    result: str | None = None


ObserverEvent = ImageEvent | StepEvent | ActionEvent | LogEvent | SplitEvent | PlanEvent


class AsyncObserver(Protocol):
    """Protocol for observing agent execution events.

    Observers receive events during agent execution, enabling
    recording, tracking, logging, or other side effects.
    """

    async def on_event(self, event: ObserverEvent) -> None:
        """Called when an agent execution event occurs.

        Args:
            event: The event that occurred during agent execution.
        """
        ...


# Deprecated: Use AsyncObserver instead
AsyncStepObserver = AsyncObserver
