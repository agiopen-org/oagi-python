# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Protocol

from .models import Action


class AsyncActionHandler(Protocol):
    async def __call__(self, actions: list[Action]) -> None:
        """
        Asynchronously executes a list of actions.

        This method takes a list of `Action` objects and executes them asynchronously.
        It is used to perform operations represented by the `Action` instances. This
        method does not return any value and modifies the system based on the input actions.

        Parameters:
            actions (list[Action]): A list of `Action` objects to be executed. Each
            `Action` must encapsulate the logic that is intended to be applied
            during the call.

        Raises:
            RuntimeError: If an error occurs during the execution of the actions.
        """
