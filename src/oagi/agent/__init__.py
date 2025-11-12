# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

# Import factories to trigger registration
from . import factories  # noqa: F401
from .default import AsyncDefaultAgent
from .protocol import Agent, AsyncAgent
from .registry import (
    async_agent_register,
    create_agent,
    get_agent_factory,
    list_agent_modes,
)
from .tasker import TaskeeAgent, TaskerAgent

__all__ = [
    "Agent",
    "AsyncAgent",
    "AsyncDefaultAgent",
    "TaskerAgent",
    "TaskeeAgent",
    "async_agent_register",
    "create_agent",
    "get_agent_factory",
    "list_agent_modes",
]
