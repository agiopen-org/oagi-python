# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from rich.console import Console
from rich.table import Table

from .tracking import StepData


def display_step_table(
    steps: list[StepData], success: bool, duration: float | None = None
):
    console = Console()

    table = Table(title="Agent Execution Summary", show_lines=True)
    table.add_column("Step", justify="center", style="cyan", width=6)
    table.add_column("Reasoning", style="white")
    table.add_column("Actions", style="yellow", width=35)
    table.add_column("Status", justify="center", width=8)

    for step in steps:
        reason = step.reasoning or "N/A"

        actions_display = []
        for action in step.actions[:3]:
            arg = action.argument[:20] if action.argument else ""
            actions_display.append(f"{action.type.value}({arg})")

        actions_str = ", ".join(actions_display)
        if len(step.actions) > 3:
            actions_str += f" (+{len(step.actions) - 3} more)"

        status_display = "✓" if step.status == "complete" else "→"

        table.add_row(
            str(step.step_num),
            reason,
            actions_str,
            status_display,
        )

    console.print(table)

    status_text = "Success" if success else "Failed/Interrupted"
    console.print(
        f"\nTotal Steps: {len(steps)} | Status: {status_text}",
        style="bold",
    )

    if duration:
        console.print(f"Duration: {duration:.2f}s")
