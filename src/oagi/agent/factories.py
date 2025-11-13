# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
from oagi.agent.tasker import TaskerAgent
from oagi.types import AsyncStepObserver

from .default import AsyncDefaultAgent
from .protocol import AsyncAgent
from .registry import async_agent_register


@async_agent_register(mode="actor")
def create_default_agent(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = "lux-v1",
    max_steps: int = 20,
    temperature: float = 0.1,
    step_observer: AsyncStepObserver | None = None,
) -> AsyncAgent:
    return AsyncDefaultAgent(
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
        step_observer=step_observer,
    )


@async_agent_register(mode="tasker")
def create_planner_agent(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = "lux-v1",
    max_steps: int = 30,
    temperature: float = 0.0,
    reflection_interval: int = 20,
    step_observer: AsyncStepObserver | None = None,
) -> AsyncAgent:
    tasker = TaskerAgent(
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
        reflection_interval=reflection_interval,
        step_observer=step_observer,
    )
    # tasker.set_task()
    return tasker
