# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from enum import Enum

from ...types import LogEvent, ObserverEvent, SplitEvent
from .exporters import export_to_html, export_to_json, export_to_markdown


class ExportFormat(str, Enum):
    """Supported export formats."""

    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


class AsyncAgentObserver:
    """Records agent execution events and exports to various formats.

    This class implements the AsyncObserver protocol and provides
    functionality for recording events during agent execution and
    exporting them to Markdown or HTML formats.
    """

    def __init__(self) -> None:
        self.events: list[ObserverEvent] = []

    async def on_event(self, event: ObserverEvent) -> None:
        """Record an event.

        Args:
            event: The event to record.
        """
        self.events.append(event)

    def add_log(self, message: str) -> None:
        """Add a custom log message.

        Args:
            message: The log message to add.
        """
        self.events.append(LogEvent(message=message))

    def add_split(self, label: str = "") -> None:
        """Add a visual separator.

        Args:
            label: Optional label for the separator.
        """
        self.events.append(SplitEvent(label=label))

    def clear(self) -> None:
        """Clear all recorded events."""
        self.events.clear()

    def get_events_by_step(self, step_num: int) -> list[ObserverEvent]:
        """Get all events for a specific step.

        Args:
            step_num: The step number to filter by.

        Returns:
            List of events for the specified step.
        """
        return [
            event
            for event in self.events
            if hasattr(event, "step_num") and event.step_num == step_num
        ]

    def export(
        self,
        format: ExportFormat | str,
        path: str,
        images_dir: str | None = None,
    ) -> None:
        """Export recorded events to a file.

        Args:
            format: Export format (markdown, html, json)
            path: Path to the output file.
            images_dir: Directory to save images (markdown only).
        """
        if isinstance(format, str):
            format = ExportFormat(format.lower())

        match format:
            case ExportFormat.MARKDOWN:
                export_to_markdown(self.events, path, images_dir)
            case ExportFormat.HTML:
                export_to_html(self.events, path)
            case ExportFormat.JSON:
                export_to_json(self.events, path)
