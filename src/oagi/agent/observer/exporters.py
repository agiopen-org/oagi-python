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
    ActionEvent,
    ImageEvent,
    LogEvent,
    ObserverEvent,
    PlanEvent,
    SplitEvent,
    StepEvent,
)


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


def export_to_html(events: list[ObserverEvent], path: str) -> None:
    """Export events to a self-contained HTML file.

    Args:
        events: List of events to export.
        path: Path to the output HTML file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html_parts: list[str] = [_get_html_header()]

    for event in events:
        timestamp = event.timestamp.strftime("%H:%M:%S")

        match event:
            case StepEvent():
                html_parts.append('<div class="step">')
                html_parts.append(f"<h2>Step {event.step_num}</h2>")
                html_parts.append(f'<span class="timestamp">{timestamp}</span>')

                if isinstance(event.image, bytes):
                    b64_image = base64.b64encode(event.image).decode("utf-8")
                    html_parts.append(
                        f'<img src="data:image/png;base64,{b64_image}" '
                        f'alt="Step {event.step_num}" class="screenshot"/>'
                    )
                elif isinstance(event.image, str):
                    html_parts.append(
                        f'<p class="url">Screenshot URL: <a href="{event.image}">{event.image}</a></p>'
                    )

                if event.step.reason:
                    html_parts.append('<div class="reasoning">')
                    html_parts.append(
                        f"<strong>Reasoning:</strong><p>{_escape_html(event.step.reason)}</p>"
                    )
                    html_parts.append("</div>")

                if event.step.actions:
                    html_parts.append('<div class="actions">')
                    html_parts.append("<strong>Planned Actions:</strong><ul>")
                    for action in event.step.actions:
                        count_str = (
                            f" (x{action.count})"
                            if action.count and action.count > 1
                            else ""
                        )
                        html_parts.append(
                            f"<li><code>{action.type.value}</code>: "
                            f"{_escape_html(action.argument)}{count_str}</li>"
                        )
                    html_parts.append("</ul></div>")

                if event.step.stop:
                    html_parts.append('<div class="complete">Task Complete</div>')

                html_parts.append("</div>")

            case ActionEvent():
                html_parts.append('<div class="action-result">')
                html_parts.append(f'<span class="timestamp">{timestamp}</span>')
                if event.error:
                    html_parts.append(
                        f'<div class="error">Error: {_escape_html(event.error)}</div>'
                    )
                else:
                    html_parts.append(
                        '<div class="success">Actions executed successfully</div>'
                    )
                html_parts.append("</div>")

            case LogEvent():
                html_parts.append('<div class="log">')
                html_parts.append(f'<span class="timestamp">{timestamp}</span>')
                html_parts.append(f"<p>{_escape_html(event.message)}</p>")
                html_parts.append("</div>")

            case SplitEvent():
                if event.label:
                    html_parts.append(
                        f'<div class="split"><h3>{_escape_html(event.label)}</h3></div>'
                    )
                else:
                    html_parts.append('<hr class="split-line"/>')

            case ImageEvent():
                pass

            case PlanEvent():
                phase_titles = {
                    "initial": "Initial Planning",
                    "reflection": "Reflection",
                    "summary": "Summary",
                }
                phase_title = phase_titles.get(event.phase, event.phase.capitalize())
                html_parts.append('<div class="plan">')
                html_parts.append(f"<h3>{phase_title}</h3>")
                html_parts.append(f'<span class="timestamp">{timestamp}</span>')

                if event.image:
                    if isinstance(event.image, bytes):
                        b64_image = base64.b64encode(event.image).decode("utf-8")
                        html_parts.append(
                            f'<img src="data:image/png;base64,{b64_image}" '
                            f'alt="{phase_title}" class="screenshot"/>'
                        )
                    elif isinstance(event.image, str):
                        html_parts.append(
                            f'<p class="url">Screenshot URL: '
                            f'<a href="{event.image}">{event.image}</a></p>'
                        )

                if event.reasoning:
                    html_parts.append('<div class="reasoning">')
                    html_parts.append(
                        f"<strong>Reasoning:</strong><p>{_escape_html(event.reasoning)}</p>"
                    )
                    html_parts.append("</div>")

                if event.result:
                    html_parts.append(
                        f'<div class="plan-result"><strong>Result:</strong> '
                        f"{_escape_html(event.result)}</div>"
                    )

                html_parts.append("</div>")

    html_parts.append(_get_html_footer())
    output_path.write_text("".join(html_parts))


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _get_html_header() -> str:
    """Get HTML document header with CSS styles."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Execution Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .step {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .step h2 {
            margin-top: 0;
            color: #007bff;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
        }
        .screenshot {
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 10px 0;
        }
        .reasoning {
            background: #f8f9fa;
            padding: 10px;
            border-left: 3px solid #007bff;
            margin: 10px 0;
        }
        .actions {
            margin: 10px 0;
        }
        .actions ul {
            margin: 5px 0;
            padding-left: 20px;
        }
        .actions code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .complete {
            background: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
        }
        .action-result {
            padding: 10px;
            margin: 5px 0;
        }
        .success {
            color: #155724;
        }
        .error {
            color: #721c24;
            background: #f8d7da;
            padding: 10px;
            border-radius: 4px;
        }
        .log {
            background: #fff3cd;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .split {
            text-align: center;
            margin: 30px 0;
        }
        .split h3 {
            color: #666;
        }
        .split-line {
            border: none;
            border-top: 2px dashed #ccc;
            margin: 30px 0;
        }
        .url {
            word-break: break-all;
        }
        .plan {
            background: #e7f3ff;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .plan h3 {
            margin-top: 0;
            color: #0056b3;
        }
        .plan-result {
            background: #d1ecf1;
            color: #0c5460;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <h1>Agent Execution Report</h1>
"""


def _get_html_footer() -> str:
    """Get HTML document footer."""
    return """
</body>
</html>
"""


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
