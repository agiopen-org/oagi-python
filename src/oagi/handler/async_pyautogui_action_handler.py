# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import asyncio

from ..types import Action
from .pyautogui_action_handler import PyautoguiActionHandler, PyautoguiConfig


class AsyncPyautoguiActionHandler:
    """
    Async wrapper for PyautoguiActionHandler that runs actions in a thread pool.

    This allows PyAutoGUI operations to be non-blocking in async contexts,
    enabling concurrent execution of other async tasks while GUI actions are performed.
    """

    def __init__(self, config: PyautoguiConfig | None = None):
        """Initialize with optional configuration.

        Args:
            config: PyautoguiConfig instance for customizing behavior
        """
        self.sync_handler = PyautoguiActionHandler(config=config)
        self.config = config or PyautoguiConfig()

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
