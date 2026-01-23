# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------


def reset_handler(handler) -> None:
    """Reset handler state if supported.

    Uses duck-typing to check if the handler has a reset() method.
    This allows handlers to reset their internal state (e.g., capslock state)
    at the start of a new automation task.

    Args:
        handler: The action handler to reset
    """
    if hasattr(handler, "reset"):
        handler.reset()


def configure_handler_delay(handler, step_delay: float) -> None:
    """Configure handler's post_batch_delay from agent's step_delay.

    Uses duck-typing to check if the handler has a config with post_batch_delay.
    This allows agents to control the delay after action execution.

    Args:
        handler: The action handler to configure
        step_delay: The delay in seconds to set
    """
    if hasattr(handler, "config") and hasattr(handler.config, "post_batch_delay"):
        handler.config.post_batch_delay = step_delay
