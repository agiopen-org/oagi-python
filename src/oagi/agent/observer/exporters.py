# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import base64
import json
from pathlib import Path

from ...types import (
    Action,
    ActionEvent,
    ActionType,
    ImageEvent,
    LogEvent,
    ObserverEvent,
    PlanEvent,
    SplitEvent,
    StepEvent,
    parse_coords,
    parse_drag_coords,
    parse_press_click,
    parse_scroll,
)


def _parse_action_coords(action: Action) -> dict | None:
    """Parse coordinates from action argument for cursor indicators.

    Returns:
        Dict with coordinates based on action type, or None if not applicable.
        - Click types: {"type": "click", "x": int, "y": int}
        - Drag: {"type": "drag", "x1": int, "y1": int, "x2": int, "y2": int}
        - Scroll: {"type": "scroll", "x": int, "y": int, "direction": str}
    """
    arg = action.argument.strip("()")

    match action.type:
        case (
            ActionType.CLICK
            | ActionType.LEFT_DOUBLE
            | ActionType.LEFT_TRIPLE
            | ActionType.RIGHT_SINGLE
            | ActionType.MOUSE_MOVE
            | ActionType.LEFT_CLICK_DRAG
        ):
            coords = parse_coords(arg)
            if coords:
                return {"type": "click", "x": coords[0], "y": coords[1]}
        case ActionType.DRAG:
            coords = parse_drag_coords(arg)
            if coords:
                return {
                    "type": "drag",
                    "x1": coords[0],
                    "y1": coords[1],
                    "x2": coords[2],
                    "y2": coords[3],
                }
        case ActionType.SCROLL:
            result = parse_scroll(arg)
            if result:
                return {
                    "type": "scroll",
                    "x": result[0],
                    "y": result[1],
                    "direction": result[2],
                }
        case ActionType.PRESS_CLICK:
            result = parse_press_click(action.argument)
            if result:
                return {"type": "click", "x": result[2], "y": result[3]}
    return None


def export_to_markdown(
    events: list[ObserverEvent],
    path: str,
    images_dir: str | None = None,
) -> None:
    """Export events to a Markdown file.

    Args:
        events: List of events to export.
        path: Path to the output Markdown file.
        images_dir: Directory to save images. If None, images are not saved.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if images_dir:
        images_path = Path(images_dir)
        images_path.mkdir(parents=True, exist_ok=True)

    lines: list[str] = ["# Agent Execution Report\n"]
    image_counter = 0

    for event in events:
        timestamp = event.timestamp.strftime("%H:%M:%S")

        match event:
            case StepEvent():
                lines.append(f"\n## Step {event.step_num}\n")
                lines.append(f"**Time:** {timestamp}\n")
                if event.task_id:
                    lines.append(f"**Task ID:** `{event.task_id}`\n")

                if isinstance(event.image, bytes):
                    if images_dir:
                        image_counter += 1
                        image_filename = f"step_{event.step_num}.png"
                        image_path = Path(images_dir) / image_filename
                        image_path.write_bytes(event.image)
                        rel_path = Path(images_dir).name / Path(image_filename)
                        lines.append(f"\n![Step {event.step_num}]({rel_path})\n")
                    else:
                        lines.append(
                            f"\n*[Screenshot captured - {len(event.image)} bytes]*\n"
                        )
                elif isinstance(event.image, str):
                    lines.append(f"\n**Screenshot URL:** {event.image}\n")

                if event.step.reason:
                    lines.append(f"\n**Reasoning:**\n> {event.step.reason}\n")

                if event.step.actions:
                    lines.append("\n**Planned Actions:**\n")
                    for action in event.step.actions:
                        count_str = (
                            f" (x{action.count})"
                            if action.count and action.count > 1
                            else ""
                        )
                        lines.append(
                            f"- `{action.type.value}`: {action.argument}{count_str}\n"
                        )

                if event.step.stop:
                    lines.append("\n**Status:** Task Complete\n")

            case ActionEvent():
                lines.append(f"\n### Actions Executed ({timestamp})\n")
                if event.error:
                    lines.append(f"\n**Error:** {event.error}\n")
                else:
                    lines.append("\n**Result:** Success\n")

            case LogEvent():
                lines.append(f"\n> **Log ({timestamp}):** {event.message}\n")

            case SplitEvent():
                if event.label:
                    lines.append(f"\n---\n\n### {event.label}\n")
                else:
                    lines.append("\n---\n")

            case ImageEvent():
                pass

            case PlanEvent():
                phase_titles = {
                    "initial": "Initial Planning",
                    "reflection": "Reflection",
                    "summary": "Summary",
                }
                phase_title = phase_titles.get(event.phase, event.phase.capitalize())
                lines.append(f"\n### {phase_title} ({timestamp})\n")
                if event.request_id:
                    lines.append(f"**Request ID:** `{event.request_id}`\n")

                if event.image:
                    if isinstance(event.image, bytes):
                        if images_dir:
                            image_counter += 1
                            image_filename = f"plan_{event.phase}_{image_counter}.png"
                            image_path = Path(images_dir) / image_filename
                            image_path.write_bytes(event.image)
                            rel_path = Path(images_dir).name / Path(image_filename)
                            lines.append(f"\n![{phase_title}]({rel_path})\n")
                        else:
                            lines.append(
                                f"\n*[Screenshot captured - {len(event.image)} bytes]*\n"
                            )
                    elif isinstance(event.image, str):
                        lines.append(f"\n**Screenshot URL:** {event.image}\n")

                if event.reasoning:
                    lines.append(f"\n**Reasoning:**\n> {event.reasoning}\n")

                if event.result:
                    lines.append(f"\n**Result:** {event.result}\n")

    output_path.write_text("".join(lines))


def _convert_events_for_html(events: list[ObserverEvent]) -> list[dict]:
    """Convert events to JSON-serializable format for HTML template."""
    result = []

    for event in events:
        timestamp = event.timestamp.strftime("%H:%M:%S")

        match event:
            case StepEvent():
                # Collect action coordinates for cursor indicators
                action_coords = []
                actions_list = []
                if event.step.actions:
                    for action in event.step.actions:
                        coords = _parse_action_coords(action)
                        if coords:
                            action_coords.append(coords)
                        actions_list.append(
                            {
                                "type": action.type.value,
                                "argument": action.argument,
                                "count": action.count or 1,
                            }
                        )

                # Handle image
                image_data = None
                if isinstance(event.image, bytes):
                    image_data = base64.b64encode(event.image).decode("utf-8")
                elif isinstance(event.image, str):
                    image_data = event.image

                result.append(
                    {
                        "event_type": "step",
                        "timestamp": timestamp,
                        "step_num": event.step_num,
                        "image": image_data,
                        "action_coords": action_coords,
                        "reason": event.step.reason,
                        "actions": actions_list,
                        "stop": event.step.stop,
                        "task_id": event.task_id,
                    }
                )

            case ActionEvent():
                result.append(
                    {
                        "event_type": "action",
                        "timestamp": timestamp,
                        "error": event.error,
                    }
                )

            case LogEvent():
                result.append(
                    {
                        "event_type": "log",
                        "timestamp": timestamp,
                        "message": event.message,
                    }
                )

            case SplitEvent():
                result.append(
                    {
                        "event_type": "split",
                        "timestamp": timestamp,
                        "label": event.label,
                    }
                )

            case ImageEvent():
                pass

            case PlanEvent():
                image_data = None
                if isinstance(event.image, bytes):
                    image_data = base64.b64encode(event.image).decode("utf-8")
                elif isinstance(event.image, str):
                    image_data = event.image

                result.append(
                    {
                        "event_type": "plan",
                        "timestamp": timestamp,
                        "phase": event.phase,
                        "image": image_data,
                        "reasoning": event.reasoning,
                        "result": event.result,
                        "request_id": event.request_id,
                    }
                )

    return result


def export_to_html(events: list[ObserverEvent], path: str) -> None:
    """Export events to a self-contained HTML file.

    Args:
        events: List of events to export.
        path: Path to the output HTML file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load template
    template_path = Path(__file__).parent / "report_template.html"
    template = template_path.read_text()

    # Convert events to JSON
    events_data = _convert_events_for_html(events)
    events_json = json.dumps(events_data)

    # Replace placeholder
    html_content = template.replace("{EVENTS_DATA}", events_json)

    output_path.write_text(html_content)


def export_to_json(events: list[ObserverEvent], path: str) -> None:
    """Export events to a JSON file.

    Args:
        events: List of events to export.
        path: Path to the output JSON file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert events to JSON-serializable format
    json_events = []
    for event in events:
        # Handle bytes images before model_dump to avoid UTF-8 decode error
        if isinstance(event, (StepEvent, ImageEvent, PlanEvent)) and isinstance(
            getattr(event, "image", None), bytes
        ):
            # Dump without json mode first, then handle bytes manually
            event_dict = event.model_dump()
            event_dict["image"] = base64.b64encode(event.image).decode("utf-8")
            event_dict["image_encoding"] = "base64"
            # Convert datetime to string
            if "timestamp" in event_dict:
                event_dict["timestamp"] = event_dict["timestamp"].isoformat()
        else:
            event_dict = event.model_dump(mode="json")
        json_events.append(event_dict)

    output_path.write_text(json.dumps(json_events, indent=2, default=str))
