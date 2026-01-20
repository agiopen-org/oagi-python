# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import asyncio

from oagi.handler.screen_manager import Screen

from ..types import Action
from .ydotool_action_handler import YdotoolActionHandler, YdotoolConfig


class AsyncYdotoolActionHandler:
    """
    Async wrapper for YdotoolActionHandler that runs actions in a thread pool.

    This allows Ydotool operations to be non-blocking in async contexts,
    enabling concurrent execution of other async tasks while GUI actions are performed.
    """

    def __init__(self, config: YdotoolConfig | None = None):
        """Initialize with optional configuration.

        Args:
            config: YdotoolConfig instance for customizing behavior
        """
        self.config = config or YdotoolConfig()
        self.sync_handler = YdotoolActionHandler(config=self.config)

    def set_target_screen(self, screen: Screen) -> None:
        """Set the target screen for the action handler.

        Args:
            screen (Screen): The screen object to set as the target.
        """
        self.sync_handler.set_target_screen(screen)

    def reset(self):
        """Reset handler state.

        Delegates to the underlying synchronous handler's reset method.
        Called at automation start/end and when FINISH action is received.
        """
        self.sync_handler.reset()

    async def __call__(self, actions: list[Action]) -> None:
        """
        Execute actions asynchronously using a thread pool executor.

        This prevents PyAutoGUI operations from blocking the async event loop,
        allowing other coroutines to run while GUI actions are being performed.

        Args:
            actions: List of actions to execute
        """
        loop = asyncio.get_event_loop()
        # Run the synchronous handler in a thread pool to avoid blocking
        await loop.run_in_executor(None, self.sync_handler, actions)
