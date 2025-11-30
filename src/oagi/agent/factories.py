# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
from oagi.agent.tasker import TaskerAgent
from oagi.constants import (
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_STEPS_TASKER,
    DEFAULT_MAX_STEPS_THINKER,
    DEFAULT_REFLECTION_INTERVAL_TASKER,
    DEFAULT_STEP_DELAY,
    DEFAULT_TEMPERATURE_LOW,
    MODEL_ACTOR,
    MODEL_THINKER,
)
from oagi.types import AsyncStepObserver

from .default import AsyncDefaultAgent
from .protocol import AsyncAgent
from .registry import async_agent_register


@async_agent_register(mode="actor")
def create_default_agent(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = MODEL_ACTOR,
    max_steps: int = DEFAULT_MAX_STEPS,
    temperature: float = DEFAULT_TEMPERATURE_LOW,
    step_observer: AsyncStepObserver | None = None,
    step_delay: float = DEFAULT_STEP_DELAY,
) -> AsyncAgent:
    return AsyncDefaultAgent(
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
        step_observer=step_observer,
        step_delay=step_delay,
    )


@async_agent_register(mode="thinker")
def create_thinker_agent(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = MODEL_THINKER,
    max_steps: int = DEFAULT_MAX_STEPS_THINKER,
    temperature: float = DEFAULT_TEMPERATURE_LOW,
    step_observer: AsyncStepObserver | None = None,
    step_delay: float = DEFAULT_STEP_DELAY,
) -> AsyncAgent:
    return AsyncDefaultAgent(
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
        step_observer=step_observer,
        step_delay=step_delay,
    )


@async_agent_register(mode="tasker")
def create_planner_agent(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = MODEL_ACTOR,
    max_steps: int = DEFAULT_MAX_STEPS_TASKER,
    temperature: float = DEFAULT_TEMPERATURE_LOW,
    reflection_interval: int = DEFAULT_REFLECTION_INTERVAL_TASKER,
    step_observer: AsyncStepObserver | None = None,
    step_delay: float = DEFAULT_STEP_DELAY,
) -> AsyncAgent:
    tasker = TaskerAgent(
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
        reflection_interval=reflection_interval,
        step_observer=step_observer,
        step_delay=step_delay,
    )
    # tasker.set_task()
    return tasker
