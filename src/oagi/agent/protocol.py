# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Protocol

from ..types import ActionHandler, AsyncActionHandler, AsyncImageProvider, ImageProvider


class Agent(Protocol):
    """Protocol for synchronous task execution agents."""

    def execute(
        self,
        instruction: str,
        action_handler: ActionHandler,
        image_provider: ImageProvider,
    ) -> bool:
        """Execute a task with the given handlers.

        Args:
            instruction: Task instruction to execute
            action_handler: Handler for executing actions
            image_provider: Provider for capturing images

        Returns:
            True if task completed successfully, False otherwise
        """
        ...


class AsyncAgent(Protocol):
    """Protocol for asynchronous task execution agents."""

    async def execute(
        self,
        instruction: str,
        action_handler: AsyncActionHandler,
        image_provider: AsyncImageProvider,
    ) -> bool:
        """Asynchronously execute a task with the given handlers.

        Args:
            instruction: Task instruction to execute
            action_handler: Handler for executing actions
            image_provider: Provider for capturing images

        Returns:
            True if task completed successfully, False otherwise
        """
        ...
