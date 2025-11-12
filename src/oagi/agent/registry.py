# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import inspect
from collections.abc import Callable
from typing import Any

from .protocol import AsyncAgent

# Type alias for agent factory functions
AgentFactory = Callable[..., AsyncAgent]

# Global registry mapping mode names to factory functions
_agent_registry: dict[str, AgentFactory] = {}


def async_agent_register(mode: str) -> Callable[[AgentFactory], AgentFactory]:
    """Decorator to register agent factory functions for specific modes.

    The decorator performs the following:
    1. Registers the factory function under the specified mode name
    2. Validates that duplicate modes are not registered
    3. Enables runtime validation of returned AsyncAgent instances

    Args:
        mode: The agent mode identifier (e.g., "actor", "planner", "todo")

    Returns:
        Decorator function that registers the factory

    Raises:
        ValueError: If the mode is already registered
    """

    def decorator(func: AgentFactory) -> AgentFactory:
        # Check if mode is already registered
        if mode in _agent_registry:
            raise ValueError(
                f"Agent mode '{mode}' is already registered. "
                f"Cannot register the same mode twice."
            )

        # Register the factory
        _agent_registry[mode] = func
        return func

    return decorator


def get_agent_factory(mode: str) -> AgentFactory:
    """Get the registered agent factory for a mode.

    Args:
        mode: The agent mode identifier

    Returns:
        The registered factory function

    Raises:
        ValueError: If the mode is not registered
    """
    if mode not in _agent_registry:
        available_modes = list(_agent_registry.keys())
        raise ValueError(
            f"Unknown agent mode: '{mode}'. Available modes: {available_modes}"
        )
    return _agent_registry[mode]


def list_agent_modes() -> list[str]:
    """List all registered agent modes.

    Returns:
        List of registered mode names
    """
    return list(_agent_registry.keys())


def create_agent(mode: str, **kwargs: Any) -> AsyncAgent:
    """Create an agent instance using the registered factory for the given mode.

    This function automatically introspects the factory's signature and only passes
    parameters that the factory accepts. This allows factories to have flexible
    signatures while callers can provide a standard set of parameters.

    Standard parameters typically include:
    - api_key: OAGI API key
    - base_url: OAGI API base URL
    - model: Model identifier (e.g., "lux-v1")
    - max_steps: Maximum number of steps to execute
    - temperature: Sampling temperature

    Args:
        mode: The agent mode identifier
        **kwargs: Parameters to pass to the factory function

    Returns:
        AsyncAgent instance created by the factory

    Raises:
        ValueError: If the mode is not registered
        TypeError: If the factory returns an object that doesn't implement AsyncAgent

    Example:
        agent = create_agent(
            mode="actor",
            api_key="...",
            base_url="...",
            model="lux-v1",
            max_steps=30,
            temperature=0.0,
        )
    """
    factory = get_agent_factory(mode)

    # Introspect factory signature to determine which parameters it accepts
    sig = inspect.signature(factory)

    # Check if factory has **kwargs parameter (VAR_KEYWORD)
    has_var_keyword = any(
        param.kind == inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values()
    )

    if has_var_keyword:
        # If factory has **kwargs, pass all parameters
        filtered_kwargs = kwargs
    else:
        # Otherwise, filter kwargs to only include parameters the factory accepts
        accepted_params = set(sig.parameters.keys())
        filtered_kwargs = {
            key: value for key, value in kwargs.items() if key in accepted_params
        }

    agent = factory(**filtered_kwargs)

    if not hasattr(agent, "execute"):
        raise TypeError(
            f"Factory for mode '{mode}' returned an object that doesn't "
            f"implement AsyncAgent protocol. Expected an object with an "
            f"'execute' method, got {type(agent).__name__}"
        )

    if not inspect.iscoroutinefunction(agent.execute):
        raise TypeError(
            f"Factory for mode '{mode}' returned an object with a non-async "
            f"'execute' method. AsyncAgent protocol requires 'execute' to be "
            f"an async method."
        )

    return agent
