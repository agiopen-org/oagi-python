# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import time

from pydantic import BaseModel, Field

from oagi.handler.screen_manager import Screen

from ..types import Action, ActionType, parse_coords, parse_drag_coords, parse_scroll
from .capslock_manager import CapsLockManager
from .wayland_support import Ydotool, get_screen_size


class YdotoolConfig(BaseModel):
    """Configuration for YdotoolActionHandler."""

    scroll_amount: int = Field(
        default=20,
        description="Amount to scroll (positive for up, negative for down)",
    )
    wait_duration: float = Field(
        default=1.0, description="Duration for wait actions in seconds"
    )
    action_pause: float = Field(
        default=0.5, description="Pause between Ydotool actions in seconds"
    )
    capslock_mode: str = Field(
        default="session",
        description="Caps lock handling mode: 'session' (internal state) or 'system' (OS-level)",
    )
    socket_address: str = Field(
        default="",
        description="Custom socket address for ydotool (e.g., '/tmp/ydotool.sock')",
    )


class YdotoolActionHandler(Ydotool):
    def __init__(self, config: YdotoolConfig | None = None) -> None:
        """
        Handles actions to be executed using Ydotool.

        This class provides functionality for handling and executing a sequence of
        actions using the Ydotool. It processes a list of actions and executes
        them as per the implementation.

        Methods:
            __call__: Executes the provided list of actions.

        Args:
            actions (list[Action]): List of actions to be processed and executed.
        """
        # Use default config if none provided
        self.config = config or YdotoolConfig()
        super().__init__(socket_address=self.config.socket_address)
        # Get screen dimensions for coordinate denormalization
        self.screen_width, self.screen_height = get_screen_size()
        # Set default delay between actions
        self.action_pause = self.config.action_pause
        # Initialize caps lock manager
        self.caps_manager = CapsLockManager(mode=self.config.capslock_mode)
        # The origin position of coordinates (the top-left corner of the screen)
        self.origin_x, self.origin_y = 0, 0

    def reset(self):
        """Reset handler state.

        Called at automation start/end and when FINISH action is received.
        Resets the internal capslock state.
        """
        self.caps_manager.reset()

    def set_target_screen(self, screen: Screen) -> None:
        """Set the target screen for the action handler.

        Args:
            screen (Screen): The screen object to set as the target.
        """
        self.screen_width, self.screen_height = screen.width, screen.height
        self.origin_x, self.origin_y = screen.x, screen.y

    def _execute_action(self, action: Action) -> bool:
        """
        Execute a group of actions and return whether FINISH is reached.
        """
        finished = False
        arg = (action.argument or "").strip()
        count = int(action.count or 1)

        match action.type:
            case ActionType.DRAG:
                x1, y1, x2, y2 = self._parse_drag_coords(arg)
                self.drag(x1, y1, x2, y2, count=count)

            case ActionType.SCROLL:
                x, y, direction = self._parse_scroll(arg)
                scroll_amount = (
                    self.config.scroll_amount
                    if direction == "up"
                    else -self.config.scroll_amount
                )
                self.scroll(scroll_amount)

            case ActionType.RIGHT_SINGLE:
                x, y = self._parse_coords(arg)
                self.click(x, y, right=True, count=count)

            case ActionType.LEFT_DOUBLE:
                x, y = self._parse_coords(arg)
                self.click(x, y, count=2 * count)

            case ActionType.LEFT_TRIPLE:
                x, y = self._parse_coords(arg)
                self.click(x, y, count=3 * count)

            case ActionType.CLICK:
                x, y = self._parse_coords(arg)
                self.click(x, y, count=count)

            case ActionType.HOTKEY:
                keys = self._parse_hotkey(arg)
                # Check if this is a caps lock key press
                if len(keys) == 1 and keys[0] == "capslock":
                    if self.caps_manager.should_use_system_capslock():
                        # System mode: use OS-level caps lock
                        self.hotkey(["capslock"])
                    else:
                        # Session mode: toggle internal state
                        self.caps_manager.toggle()
                else:
                    # Regular hotkey combination
                    self.hotkey(keys, count=count)

            case ActionType.TYPE:
                # Remove quotes if present
                text = arg.strip("\"'")
                # Apply caps lock transformation if needed
                text = self.caps_manager.transform_text(text)
                self._run_ydotool(["type", text], count=count)

            case ActionType.FINISH:
                # Task completion - reset handler state
                self.reset()

            case ActionType.WAIT:
                # Wait for a short period
                time.sleep(self.config.wait_duration)

            case ActionType.CALL_USER:
                # Call user - implementation depends on requirements
                print("User intervention requested")

            case _:
                print(f"Unknown action type: {action.type}")

        return finished

    def _denormalize_coords(self, x: float, y: float) -> tuple[int, int]:
        """Convert coordinates from 0-1000 range to actual screen coordinates.

        Also handles corner coordinates to prevent PyAutoGUI fail-safe trigger.
        Corner coordinates (0,0), (0,max), (max,0), (max,max) are offset by 1 pixel.
        """
        screen_x = int(x * self.screen_width / 1000)
        screen_y = int(y * self.screen_height / 1000)

        # Prevent fail-safe by adjusting corner coordinates
        # Check if coordinates are at screen corners (with small tolerance)
        if screen_x < 1:
            screen_x = 1
        elif screen_x > self.screen_width - 1:
            screen_x = self.screen_width - 1

        if screen_y < 1:
            screen_y = 1
        elif screen_y > self.screen_height - 1:
            screen_y = self.screen_height - 1

        # Add origin offset to convert relative to top-left corner
        screen_x += self.origin_x
        screen_y += self.origin_y

        return screen_x, screen_y

    def _normalize_key(self, key: str) -> str:
        """Normalize key names for consistency."""
        key = key.strip().lower()
        # Normalize caps lock variations
        hotkey_variations_mapping = {
            "capslock": ["caps_lock", "caps", "capslock"],
            "pgup": ["page_up", "pageup"],
            "pgdn": ["page_down", "pagedown"],
        }
        for normalized, variations in hotkey_variations_mapping.items():
            if key in variations:
                return normalized
        return key

    def _parse_coords(self, args_str: str) -> tuple[int, int]:
        """Extract x, y coordinates from argument string."""
        coords = parse_coords(args_str)
        if not coords:
            raise ValueError(f"Invalid coordinates format: {args_str}")
        return self._denormalize_coords(coords[0], coords[1])

    def _parse_drag_coords(self, args_str: str) -> tuple[int, int, int, int]:
        """Extract x1, y1, x2, y2 coordinates from drag argument string."""
        coords = parse_drag_coords(args_str)
        if not coords:
            raise ValueError(f"Invalid drag coordinates format: {args_str}")
        x1, y1 = self._denormalize_coords(coords[0], coords[1])
        x2, y2 = self._denormalize_coords(coords[2], coords[3])
        return x1, y1, x2, y2

    def _parse_scroll(self, args_str: str) -> tuple[int, int, str]:
        """Extract x, y, direction from scroll argument string."""
        result = parse_scroll(args_str)
        if not result:
            raise ValueError(f"Invalid scroll format: {args_str}")
        x, y = self._denormalize_coords(result[0], result[1])
        return x, y, result[2]

    def _parse_hotkey(self, args_str: str) -> list[str]:
        """Parse hotkey string into list of keys."""
        # Remove parentheses if present
        args_str = args_str.strip("()")
        # Split by '+' to get individual keys
        keys = [self._normalize_key(key) for key in args_str.split("+")]
        return keys

    def __call__(self, actions: list[Action]) -> None:
        """Execute the provided list of actions."""
        for action in actions:
            try:
                self._execute_action(action)
            except Exception as e:
                print(f"Error executing action {action.type}: {e}")
                raise
