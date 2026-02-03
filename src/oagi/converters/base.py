# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""Base class for action converters.

This module provides the abstract base class for converting model-specific
actions to pyautogui command strings for remote execution.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ..handler.capslock_manager import CapsLockManager
from ..handler.utils import (
    CoordinateScaler,
    normalize_key,
    parse_hotkey,
    validate_keys,
)

T = TypeVar("T")


@dataclass
class ConverterConfig:
    """Configuration for action converters.

    Matches the configuration options in PyautoguiConfig for consistency.
    """

    sandbox_width: int = 1920
    sandbox_height: int = 1080
    drag_duration: float = 0.5
    scroll_amount: int = 2
    wait_duration: float = 1.0
    hotkey_interval: float = 0.1
    capslock_mode: str = "session"
    strict_coordinate_validation: bool = False
    """If True, raise ValueError when coordinates are outside valid range.
    If False (default), clamp coordinates to valid range (original behavior)."""


class BaseActionConverter(ABC, Generic[T]):
    """Abstract base class for action converters.

    Subclasses must implement:
    - coord_width/coord_height properties for input coordinate space
    - _convert_single_action() for model-specific conversion logic
    - serialize_actions() for trajectory logging

    Provides common functionality:
    - Coordinate scaling via CoordinateScaler
    - Key normalization via shared utils
    - __call__ interface returning list of action strings
    - action_string_to_step() for runtime API format
    """

    def __init__(
        self,
        *,
        config: ConverterConfig | None = None,
        logger: Any | None = None,
    ):
        """Initialize the converter.

        Args:
            config: Converter configuration. Uses defaults if not provided.
            logger: Optional logger instance for debug/error logging.
        """
        self.config = config or ConverterConfig()
        self.logger = logger

        # Initialize coordinate scaler
        self._coord_scaler = CoordinateScaler(
            source_width=self.coord_width,
            source_height=self.coord_height,
            target_width=self.config.sandbox_width,
            target_height=self.config.sandbox_height,
        )

        # Initialize caps lock manager
        self.caps_manager = CapsLockManager(mode=self.config.capslock_mode)

        # Track last cursor position (for actions without explicit coordinates)
        self._last_x: int | None = None
        self._last_y: int | None = None

    @property
    @abstractmethod
    def coord_width(self) -> int:
        """Input coordinate space width (e.g., 1024 for XGA, 1000 for OAGI)."""
        ...

    @property
    @abstractmethod
    def coord_height(self) -> int:
        """Input coordinate space height (e.g., 768 for XGA, 1000 for OAGI)."""
        ...

    @property
    def scale_x(self) -> float:
        """X scaling factor from input to sandbox coordinates."""
        return self._coord_scaler.scale_x

    @property
    def scale_y(self) -> float:
        """Y scaling factor from input to sandbox coordinates."""
        return self._coord_scaler.scale_y

    def scale_coordinate(self, x: int | float, y: int | float) -> tuple[int, int]:
        """Scale coordinates from model space to sandbox space.

        Args:
            x: X coordinate in model space
            y: Y coordinate in model space

        Returns:
            Tuple of (scaled_x, scaled_y) in sandbox space
        """
        return self._coord_scaler.scale(x, y)

    def normalize_key(self, key: str) -> str:
        """Normalize a key name to pyautogui format.

        Args:
            key: Key name to normalize

        Returns:
            Normalized key name
        """
        return normalize_key(key)

    def parse_hotkey(self, hotkey_str: str, *, validate: bool = True) -> list[str]:
        """Parse a hotkey string into a list of normalized key names.

        Args:
            hotkey_str: Hotkey string (e.g., "ctrl+c")
            validate: If True, validate keys against PYAUTOGUI_VALID_KEYS

        Returns:
            List of normalized key names
        """
        return parse_hotkey(hotkey_str, validate=validate)

    def validate_keys(self, keys: list[str]) -> None:
        """Validate that all keys are recognized by pyautogui.

        Args:
            keys: List of key names to validate

        Raises:
            ValueError: If any key is invalid
        """
        validate_keys(keys)

    def _get_last_or_center(self) -> tuple[int, int]:
        """Get last cursor position or screen center as fallback.

        Returns:
            Tuple of (x, y) coordinates
        """
        if self._last_x is not None and self._last_y is not None:
            return self._last_x, self._last_y
        return self.config.sandbox_width // 2, self.config.sandbox_height // 2

    def _log_error(self, message: str) -> None:
        """Log an error message if logger is available."""
        if self.logger:
            self.logger.error(message)

    def _log_info(self, message: str) -> None:
        """Log an info message if logger is available."""
        if self.logger:
            self.logger.info(message)

    def _log_debug(self, message: str) -> None:
        """Log a debug message if logger is available."""
        if self.logger:
            self.logger.debug(message)

    def __call__(self, actions: list[T]) -> list[str]:
        """Convert actions to list of pyautogui command strings.

        Args:
            actions: List of model-specific action objects

        Returns:
            List of pyautogui command strings

        Raises:
            RuntimeError: If all action conversions failed
        """
        converted: list[str] = []
        failed: list[tuple[str, str]] = []
        skipped: list[str] = []

        if not actions:
            return converted

        for action in actions:
            try:
                action_strings = self._convert_single_action(action)

                if not action_strings:
                    # No-op action (e.g., screenshot, cursor_position)
                    action_type = getattr(action, "action_type", repr(action))
                    skipped.append(str(action_type))
                    continue

                converted.extend(action_strings)

            except Exception as e:
                action_repr = repr(action)
                self._log_error(f"Failed to convert action: {action_repr}, error: {e}")
                failed.append((action_repr, str(e)))

        if skipped:
            self._log_debug(f"Skipped no-op actions: {skipped}")

        if not converted and actions and failed:
            raise RuntimeError(
                f"All action conversions failed ({len(failed)}/{len(actions)}): {failed}"
            )

        return converted

    @abstractmethod
    def _convert_single_action(self, action: T) -> list[str]:
        """Convert a single action to pyautogui command string(s).

        Args:
            action: Model-specific action object

        Returns:
            List of pyautogui command strings (may be empty for no-op actions)

        Raises:
            ValueError: If action format is invalid
        """
        ...

    @abstractmethod
    def serialize_actions(self, actions: list[T]) -> list[dict[str, Any]]:
        """Serialize actions for trajectory logging.

        Args:
            actions: List of model-specific action objects

        Returns:
            List of serialized action dictionaries
        """
        ...

    def action_string_to_step(self, action: str) -> dict[str, Any]:
        """Convert an action string into a step for runtime/do API.

        Args:
            action: Action string (e.g., "pyautogui.click(x=100, y=200)")

        Returns:
            Step dict for runtime API
        """
        action_str = str(action).strip()

        # Special markers
        upper = action_str.upper()
        if upper in ["DONE", "FAIL"]:
            return {"type": "sleep", "parameters": {"seconds": 0}}

        # WAIT(seconds)
        wait_match = re.match(
            r"^WAIT\((?P<sec>[0-9]*\.?[0-9]+)\)$", action_str, re.IGNORECASE
        )
        if wait_match:
            seconds = float(wait_match.group("sec"))
            return {"type": "sleep", "parameters": {"seconds": seconds}}

        # pyautogui code path
        if "pyautogui" in action_str.lower():
            return {
                "type": "pyautogui",
                "parameters": {"code": action_str},
            }

        # Default: shell command
        return {"type": "execute", "parameters": {"command": action_str, "shell": True}}
