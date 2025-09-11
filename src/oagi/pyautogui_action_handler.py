# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import re
import time

import pyautogui
from pydantic import BaseModel, Field

from .types import Action, ActionType


class PyautoguiConfig(BaseModel):
    """Configuration for PyautoguiActionHandler."""

    drag_duration: float = Field(
        default=0.5, description="Duration for drag operations in seconds"
    )
    scroll_amount: int = Field(
        default=30, description="Amount to scroll (positive for up, negative for down)"
    )
    wait_duration: float = Field(
        default=1.0, description="Duration for wait actions in seconds"
    )
    action_pause: float = Field(
        default=0.1, description="Pause between PyAutoGUI actions in seconds"
    )


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

    def __init__(self, config: PyautoguiConfig | None = None):
        # Use default config if none provided
        self.config = config or PyautoguiConfig()
        # Get screen dimensions for coordinate denormalization
        self.screen_width, self.screen_height = pyautogui.size()
        # Set default delay between actions
        pyautogui.PAUSE = self.config.action_pause

    def _denormalize_coords(self, x: float, y: float) -> tuple[int, int]:
        """Convert coordinates from 0-1000 range to actual screen coordinates."""
        screen_x = int(x * self.screen_width / 1000)
        screen_y = int(y * self.screen_height / 1000)
        return screen_x, screen_y

    def _parse_coords(self, args_str: str) -> tuple[int, int]:
        """Extract x, y coordinates from argument string."""
        match = re.match(r"(\d+),\s*(\d+)", args_str)
        if not match:
            raise ValueError(f"Invalid coordinates format: {args_str}")
        x, y = int(match.group(1)), int(match.group(2))
        return self._denormalize_coords(x, y)

    def _parse_drag_coords(self, args_str: str) -> tuple[int, int, int, int]:
        """Extract x1, y1, x2, y2 coordinates from drag argument string."""
        match = re.match(r"(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", args_str)
        if not match:
            raise ValueError(f"Invalid drag coordinates format: {args_str}")
        x1, y1, x2, y2 = (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
        )
        x1, y1 = self._denormalize_coords(x1, y1)
        x2, y2 = self._denormalize_coords(x2, y2)
        return x1, y1, x2, y2

    def _parse_scroll(self, args_str: str) -> tuple[int, int, str]:
        """Extract x, y, direction from scroll argument string."""
        match = re.match(r"(\d+),\s*(\d+),\s*(\w+)", args_str)
        if not match:
            raise ValueError(f"Invalid scroll format: {args_str}")
        x, y = int(match.group(1)), int(match.group(2))
        x, y = self._denormalize_coords(x, y)
        direction = match.group(3).lower()
        return x, y, direction

    def _parse_hotkey(self, args_str: str) -> list[str]:
        """Parse hotkey string into list of keys."""
        # Remove parentheses if present
        args_str = args_str.strip("()")
        # Split by '+' to get individual keys
        keys = [key.strip() for key in args_str.split("+")]
        return keys

    def _execute_single_action(self, action: Action) -> None:
        """Execute a single action once."""
        arg = action.argument.strip("()")  # Remove outer parentheses if present

        match action.type:
            case ActionType.CLICK:
                x, y = self._parse_coords(arg)
                pyautogui.click(x, y)

            case ActionType.LEFT_DOUBLE:
                x, y = self._parse_coords(arg)
                pyautogui.doubleClick(x, y)

            case ActionType.LEFT_TRIPLE:
                x, y = self._parse_coords(arg)
                pyautogui.tripleClick(x, y)

            case ActionType.RIGHT_SINGLE:
                x, y = self._parse_coords(arg)
                pyautogui.rightClick(x, y)

            case ActionType.DRAG:
                x1, y1, x2, y2 = self._parse_drag_coords(arg)
                pyautogui.moveTo(x1, y1)
                pyautogui.dragTo(
                    x2, y2, duration=self.config.drag_duration, button="left"
                )

            case ActionType.HOTKEY:
                keys = self._parse_hotkey(arg)
                pyautogui.hotkey(*keys)

            case ActionType.TYPE:
                # Remove quotes if present
                text = arg.strip("\"'")
                pyautogui.typewrite(text)

            case ActionType.SCROLL:
                x, y, direction = self._parse_scroll(arg)
                pyautogui.moveTo(x, y)
                scroll_amount = (
                    self.config.scroll_amount
                    if direction == "up"
                    else -self.config.scroll_amount
                )
                pyautogui.scroll(scroll_amount)

            case ActionType.FINISH:
                # Task completion - no action needed
                pass

            case ActionType.WAIT:
                # Wait for a short period
                time.sleep(self.config.wait_duration)

            case ActionType.CALL_USER:
                # Call user - implementation depends on requirements
                print("User intervention requested")

            case _:
                print(f"Unknown action type: {action.type}")

    def _execute_action(self, action: Action) -> None:
        """Execute an action, potentially multiple times."""
        count = action.count or 1

        for _ in range(count):
            self._execute_single_action(action)

    def __call__(self, actions: list[Action]) -> None:
        """Execute the provided list of actions."""
        for action in actions:
            try:
                self._execute_action(action)
            except Exception as e:
                print(f"Error executing action {action.type}: {e}")
                raise
