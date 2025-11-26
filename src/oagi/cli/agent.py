# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import argparse
import asyncio
import os
import sys
import time
import traceback

from oagi.agent.observer import AsyncAgentObserver
from oagi.exceptions import check_optional_dependency

from .display import display_step_table
from .tracking import StepTracker


def add_agent_parser(subparsers: argparse._SubParsersAction) -> None:
    agent_parser = subparsers.add_parser("agent", help="Agent execution commands")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command", required=True)

    # agent run command
    run_parser = agent_subparsers.add_parser(
        "run", help="Run an agent with the given instruction"
    )
    run_parser.add_argument(
        "instruction", type=str, help="Task instruction for the agent to execute"
    )
    run_parser.add_argument(
        "--model", type=str, help="Model to use (default: lux-actor-1)"
    )
    run_parser.add_argument(
        "--max-steps", type=int, help="Maximum number of steps (default: 20)"
    )
    run_parser.add_argument(
        "--temperature", type=float, help="Sampling temperature (default: 0.5)"
    )
    run_parser.add_argument(
        "--mode",
        type=str,
        default="actor",
        help="Agent mode to use (default: actor). Available modes: actor, planner",
    )
    run_parser.add_argument(
        "--oagi-api-key", type=str, help="OAGI API key (default: OAGI_API_KEY env var)"
    )
    run_parser.add_argument(
        "--oagi-base-url",
        type=str,
        help="OAGI base URL (default: https://api.agiopen.org, or OAGI_BASE_URL env var)",
    )
    run_parser.add_argument(
        "--export",
        type=str,
        choices=["markdown", "html", "json"],
        help="Export execution history to file (markdown, html, or json)",
    )
    run_parser.add_argument(
        "--export-file",
        type=str,
        help="Output file path for export (default: execution_report.[md|html|json])",
    )
    run_parser.add_argument(
        "--step-delay",
        type=float,
        help="Delay in seconds after each step before next screenshot (default: 0.3)",
    )

    # agent permission command
    agent_subparsers.add_parser(
        "permission",
        help="Check macOS permissions for screen recording and accessibility",
    )


def handle_agent_command(args: argparse.Namespace) -> None:
    if args.agent_command == "run":
        run_agent(args)
    elif args.agent_command == "permission":
        check_permissions()


def check_permissions() -> None:
    """Check and request macOS permissions for screen recording and accessibility.

    Guides the user through granting permissions one at a time.
    """
    if sys.platform != "darwin":
        print("Warning: Permission check is only applicable on macOS.")
        print("On other platforms, no special permissions are required.")
        return

    check_optional_dependency("Quartz", "Permission check", "desktop")
    check_optional_dependency("ApplicationServices", "Permission check", "desktop")

    import subprocess  # noqa: PLC0415

    from ApplicationServices import AXIsProcessTrusted  # noqa: PLC0415
    from Quartz import (  # noqa: PLC0415
        CGPreflightScreenCaptureAccess,
        CGRequestScreenCaptureAccess,
    )

    # Check all permissions first to show status
    screen_recording_granted = CGPreflightScreenCaptureAccess()
    accessibility_granted = AXIsProcessTrusted()

    print("Checking permissions...")
    print(f"  {'[OK]' if screen_recording_granted else '[MISSING]'} Screen Recording")
    print(f"  {'[OK]' if accessibility_granted else '[MISSING]'} Accessibility")

    # Guide user through missing permissions one at a time
    if not screen_recording_granted:
        CGRequestScreenCaptureAccess()
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
            ],
            check=False,
        )
        print("\nPlease grant Screen Recording permission in System Preferences.")
        print("After granting, run this command again to continue.")
        print("Note: You may need to restart your terminal after granting permissions.")
        sys.exit(1)

    if not accessibility_granted:
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ],
            check=False,
        )
        print("\nPlease grant Accessibility permission in System Preferences.")
        print("After granting, run this command again to continue.")
        print("Note: You may need to restart your terminal after granting permissions.")
        sys.exit(1)

    print()
    print("All permissions granted. You can run the agent.")


def _warn_missing_permissions() -> None:
    if sys.platform != "darwin":
        return

    if not check_optional_dependency(
        "Quartz", "Permission check", "desktop", raise_error=False
    ):
        return
    if not check_optional_dependency(
        "ApplicationServices", "Permission check", "desktop", raise_error=False
    ):
        return

    from ApplicationServices import AXIsProcessTrusted  # noqa: PLC0415
    from Quartz import CGPreflightScreenCaptureAccess  # noqa: PLC0415

    missing = []
    if not CGPreflightScreenCaptureAccess():
        missing.append("Screen Recording")
    if not AXIsProcessTrusted():
        missing.append("Accessibility")

    if missing:
        print(f"Warning: Missing macOS permissions: {', '.join(missing)}")
        print("Run 'oagi agent permission' to configure permissions.\n")


def run_agent(args: argparse.Namespace) -> None:
    # Check if desktop extras are installed
    check_optional_dependency("pyautogui", "Agent execution", "desktop")
    check_optional_dependency("PIL", "Agent execution", "desktop")

    # Warn about missing macOS permissions (non-blocking)
    _warn_missing_permissions()

    from oagi import AsyncPyautoguiActionHandler, AsyncScreenshotMaker  # noqa: PLC0415
    from oagi.agent import create_agent  # noqa: PLC0415

    # Get configuration
    api_key = args.oagi_api_key or os.getenv("OAGI_API_KEY")
    if not api_key:
        print(
            "Error: OAGI API key not provided.\n"
            "Set OAGI_API_KEY environment variable or use --oagi-api-key flag.",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = args.oagi_base_url or os.getenv(
        "OAGI_BASE_URL", "https://api.agiopen.org"
    )
    model = args.model or "lux-actor-1"
    max_steps = args.max_steps or 20
    temperature = args.temperature if args.temperature is not None else 0.5
    mode = args.mode or "actor"
    step_delay = args.step_delay if args.step_delay is not None else 0.3
    export_format = args.export
    export_file = args.export_file

    # Create observers
    step_tracker = StepTracker()
    agent_observer = AsyncAgentObserver() if export_format else None

    # Use a combined observer that forwards to both
    class CombinedObserver:
        async def on_event(self, event):
            await step_tracker.on_event(event)
            if agent_observer:
                await agent_observer.on_event(event)

    observer = CombinedObserver()

    # Create agent with observer
    agent = create_agent(
        mode=mode,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
        step_observer=observer,
        step_delay=step_delay,
    )

    # Create handlers
    action_handler = AsyncPyautoguiActionHandler()
    image_provider = AsyncScreenshotMaker()

    print(f"Starting agent with instruction: {args.instruction}")
    print(
        f"Mode: {mode}, Model: {model}, Max steps: {max_steps}, "
        f"Temperature: {temperature}, Step delay: {step_delay}s"
    )
    print("-" * 60)

    start_time = time.time()
    success = False
    interrupted = False

    try:
        success = asyncio.run(
            agent.execute(
                instruction=args.instruction,
                action_handler=action_handler,
                image_provider=image_provider,
            )
        )
    except KeyboardInterrupt:
        print("\nAgent execution interrupted by user (Ctrl+C)")
        interrupted = True
    except Exception as e:
        print(f"\nError during agent execution: {e}", file=sys.stderr)
        traceback.print_exc()
    finally:
        duration = time.time() - start_time

        if step_tracker.steps:
            print("\n" + "=" * 60)
            display_step_table(step_tracker.steps, success, duration)
        else:
            print("\nNo steps were executed.")

        # Export if requested
        if export_format and agent_observer:
            # Determine output file path
            if export_file:
                output_path = export_file
            else:
                ext_map = {"markdown": "md", "html": "html", "json": "json"}
                output_path = f"execution_report.{ext_map[export_format]}"

            try:
                agent_observer.export(export_format, output_path)
                print(f"\nExecution history exported to: {output_path}")
            except Exception as e:
                print(f"\nError exporting execution history: {e}", file=sys.stderr)

        if interrupted:
            sys.exit(130)
        elif not success:
            sys.exit(1)
