# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime

from oagi.types import Action


@dataclass
class StepData:
    step_num: int
    timestamp: datetime
    reasoning: str | None
    actions: list[Action]
    action_count: int
    status: str


class StepTracker:
    """Tracks agent step execution by implementing AsyncStepObserver protocol."""

    def __init__(self):
        self.steps: list[StepData] = []

    async def on_step(
        self,
        step_num: int,
        reasoning: str | None,
        actions: list[Action],
    ) -> None:
        step_data = StepData(
            step_num=step_num,
            timestamp=datetime.now(),
            reasoning=reasoning,
            actions=actions,
            action_count=len(actions),
            status="running",
        )
        self.steps.append(step_data)
