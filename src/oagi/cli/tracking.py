# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime

from oagi.types import Action, ActionEvent, ObserverEvent, StepEvent


@dataclass
class StepData:
    step_num: int
    timestamp: datetime
    reasoning: str | None
    actions: list[Action]
    action_count: int
    status: str


class StepTracker:
    """Tracks agent step execution by implementing AsyncObserver protocol."""

    def __init__(self):
        self.steps: list[StepData] = []

    async def on_event(self, event: ObserverEvent) -> None:
        """Handle observer events.

        Args:
            event: The observer event to handle.
        """
        match event:
            case StepEvent():
                step_data = StepData(
                    step_num=event.step_num,
                    timestamp=event.timestamp,
                    reasoning=event.step.reason,
                    actions=event.step.actions,
                    action_count=len(event.step.actions),
                    status="running",
                )
                self.steps.append(step_data)
            case ActionEvent():
                # Update status of corresponding step
                for step in self.steps:
                    if step.step_num == event.step_num:
                        step.status = "error" if event.error else "completed"
                        break
            case _:
                pass
