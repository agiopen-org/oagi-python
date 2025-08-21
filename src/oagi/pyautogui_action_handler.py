# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from .types import Action


class PyautoguiActionHandler:
    """
    Handles actions to be executed using PyAutoGUI.

    This class provides functionality for handling and executing a sequence of
    actions using the PyAutoGUI library. It processes a list of actions and executes
    them as per the implementation.

    Methods:
        __call__: Executes the provided list of actions.

    Args:
        actions (list[Action]): List of actions to be processed and executed.
    """

    def __call__(self, actions: list[Action]) -> None:
        print(actions)
        pass
