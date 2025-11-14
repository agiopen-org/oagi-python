# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Protocol

from .models import Action


class AsyncStepObserver(Protocol):
    """Protocol for observing agent step execution.

    Observers receive step information (reasoning and actions) as agents
    execute tasks, enabling tracking, logging, or other side effects.
    """

    async def on_step(
        self,
        step_num: int,
        reasoning: str | None,
        actions: list[Action],
    ) -> None:
        """Called when an agent executes a step.

        Args:
            step_num: The step number (1-indexed)
            reasoning: The reasoning/thinking for this step (if available)
            actions: The list of actions being executed in this step
        """
        ...
