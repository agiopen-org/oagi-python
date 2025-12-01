# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------


class CapsLockManager:
    """Manages caps lock state for text transformation.

    This class maintains an internal caps lock state that can be toggled
    independently of the system's caps lock state. This allows for consistent
    text case handling during automation regardless of the system state.
    """

    def __init__(self, mode: str = "session"):
        """Initialize caps lock manager.

        Args:
            mode: Either "session" (internal state) or "system" (OS-level)
        """
        self.mode = mode
        self.caps_enabled = False

    def reset(self):
        """Reset caps lock state to default (off).

        Called at automation start/end and when FINISH action is received.
        """
        self.caps_enabled = False

    def toggle(self):
        """Toggle caps lock state in session mode."""
        if self.mode == "session":
            self.caps_enabled = not self.caps_enabled

    def transform_text(self, text: str) -> str:
        """Transform text based on caps lock state.

        Args:
            text: Input text to transform

        Returns:
            Transformed text (uppercase alphabets if caps enabled in session mode)
        """
        if self.mode == "session" and self.caps_enabled:
            # Transform letters to uppercase, preserve special characters
            return "".join(c.upper() if c.isalpha() else c for c in text)
        return text

    def should_use_system_capslock(self) -> bool:
        """Check if system-level caps lock should be used."""
        return self.mode == "system"
