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


@async_agent_register(mode="tasker:cvs_appointment")
def create_cvs_appointment_agent(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = MODEL_ACTOR,
    max_steps: int = DEFAULT_MAX_STEPS_TASKER,
    temperature: float = DEFAULT_TEMPERATURE_LOW,
    reflection_interval: int = DEFAULT_REFLECTION_INTERVAL_TASKER,
    step_observer: AsyncStepObserver | None = None,
    step_delay: float = DEFAULT_STEP_DELAY,
    # CVS-specific parameters
    first_name: str = "First",
    last_name: str = "Last",
    email: str = "user@example.com",
    birthday: str = "01-01-1990",  # MM-DD-YYYY
    zip_code: str = "00000",
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

    month, day, year = birthday.split("-")
    instruction = (
        f"Schedule an appointment at CVS for {first_name} {last_name} "
        f"with email {email} and birthday {birthday}"
    )
    todos = [
        "Open a new tab, go to www.cvs.com, type 'flu shot' in the search bar and press enter, "
        "wait for the page to load, then click on the button of Schedule vaccinations on the "
        "top of the page",
        f"Enter the first name '{first_name}', last name '{last_name}', and email '{email}' "
        "in the form. Do not use any suggested autofills. Make sure the mobile phone number "
        "is empty.",
        f"Slightly scroll down to see the date of birth, enter Month '{month}', Day '{day}', "
        f"and Year '{year}' in the form",
        "Click on 'Continue as guest' button, wait for the page to load with wait, "
        "click on 'Add vaccines' button, select 'Flu' and click on 'Add vaccines'",
        f"Click on 'next' to enter the page with recommendation vaccines, then click on "
        f"'next' again, until on the page of entering zip code, enter '{zip_code}', select "
        "the first option from the dropdown menu, and click on 'Search'",
    ]

    tasker.set_task(instruction, todos)
    return tasker


@async_agent_register(mode="tasker:software_qa")
def create_software_qa_agent(
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

    instruction = "QA: click through every sidebar button in the Nuclear Player UI"
    todos = [
        "Click on 'Dashboard' in the left sidebar",
        "Click on 'Downloads' in the left sidebar",
        "Click on 'Lyrics' in the left sidebar",
        "Click on 'Plugins' in the left sidebar",
        "Click on 'Search Results' in the left sidebar",
        "Click on 'Settings' in the left sidebar",
        "Click on 'Equalizer' in the left sidebar",
        "Click on 'Visualizer' in the left sidebar",
        "Click on 'Listening History' in the left sidebar",
        "Click on 'Favorite Albums' in the left sidebar",
        "Click on 'Favorite Tracks' in the left sidebar",
        "Click on 'Favorite Artists' in the left sidebar",
        "Click on 'Local Library' in the left sidebar",
        "Click on 'Playlists' in the left sidebar",
    ]

    tasker.set_task(instruction, todos)
    return tasker
