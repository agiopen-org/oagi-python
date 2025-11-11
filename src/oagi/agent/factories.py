# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from .default import AsyncDefaultAgent
from .planner.planner_agent import PlannerAgent
from .protocol import AsyncAgent
from .registry import async_agent_register


@async_agent_register(mode="actor")
def create_default_agent(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = "lux-v1",
    max_steps: int = 20,
    temperature: float = 0.1,
) -> AsyncAgent:
    return AsyncDefaultAgent(
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
    )


@async_agent_register(mode="planner")
def create_planner_agent(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = "lux-v1",
    max_steps: int = 30,
    temperature: float = 0.0,
    reflection_interval: int = 20,
) -> AsyncAgent:
    planner = PlannerAgent(
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
        reflection_interval=reflection_interval,
    )
    # planner.set_task()
    return planner
