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
from oagi.constants import (
    API_KEY_HELP_URL,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_STEPS_THINKER,
    DEFAULT_STEP_DELAY,
    MODE_ACTOR,
    MODEL_THINKER,
)
from oagi.exceptions import check_optional_dependency
from oagi.handler.screen_manager import ScreenManager

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
        "instruction",
        type=str,
        nargs="?",
        default="",
        help="Task instruction for the agent to execute (optional for pre-configured modes)",
    )
    run_parser.add_argument(
        "--model", type=str, help="Model to use (default: determined by mode)"
    )
    run_parser.add_argument(
        "--max-steps",
        type=int,
        help="Maximum number of steps (default: determined by mode)",
    )
    run_parser.add_argument(
        "--temperature",
        type=float,
        help="Sampling temperature (default: determined by mode)",
    )
    run_parser.add_argument(
        "--mode",
        type=str,
        default=MODE_ACTOR,
        help=f"Agent mode to use (default: {MODE_ACTOR}). Use 'oagi agent modes' to list available modes",
    )
    run_parser.add_argument(
        "--oagi-api-key", type=str, help="OAGI API key (default: OAGI_API_KEY env var)"
    )
    run_parser.add_argument(
        "--oagi-base-url",
        type=str,
        help=f"OAGI base URL (default: {DEFAULT_BASE_URL}, or OAGI_BASE_URL env var)",
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
        help=f"Delay in seconds after each step before next screenshot (default: {DEFAULT_STEP_DELAY})",
    )
    run_parser.add_argument(
        "--screen",
        type=str,
        help="Choose screen to run the task (default: primary)",
    )

    # agent modes command
    agent_subparsers.add_parser("modes", help="List available agent modes")

    # agent permission command
    agent_subparsers.add_parser(
        "permission",
        help="Check macOS permissions for screen recording and accessibility",
    )


def handle_agent_command(args: argparse.Namespace) -> None:
    if args.agent_command == "run":
        run_agent(args)
    elif args.agent_command == "modes":
        list_modes()
    elif args.agent_command == "permission":
        check_permissions()


def list_modes() -> None:
    """List all available agent modes."""
    from oagi.agent import list_agent_modes  # noqa: PLC0415

    modes = list_agent_modes()
    print("Available agent modes:")
    for mode in modes:
        print(f"  - {mode}")


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
    check_optional_dependency("PIL", "Agent execution", "desktop")

    from oagi import AsyncScreenshotMaker  # noqa: PLC0415
    from oagi.agent import create_agent  # noqa: PLC0415
    from oagi.handler.wayland_support import is_wayland_display_server  # noqa: PLC0415

    # ScreenManager for multi-monitor support
    # Must be initialized before pyautogui to ensure correct DPI awareness
    screen_manager = ScreenManager()
    # Select appropriate action handler based on display server
    if is_wayland_display_server():
        check_optional_dependency("screeninfo", "Agent execution (Wayland)", "desktop")
        from oagi import AsyncYdotoolActionHandler  # noqa: PLC0415

        action_handler = AsyncYdotoolActionHandler()
    else:
        check_optional_dependency("pyautogui", "Agent execution", "desktop")
        # Warn about missing macOS permissions (non-blocking)
        _warn_missing_permissions()
        from oagi import AsyncPyautoguiActionHandler  # noqa: PLC0415

        action_handler = AsyncPyautoguiActionHandler()

    # Get configuration
    api_key = args.oagi_api_key or os.getenv("OAGI_API_KEY")
    if not api_key:
        print(
            "Error: OAGI API key not provided.\n"
            "Set OAGI_API_KEY environment variable or use --oagi-api-key flag.\n"
            f"Get your API key at {API_KEY_HELP_URL}",
            file=sys.stderr,
        )
        sys.exit(1)

    # screen_manager.enable_windows_dpi_awareness()
    base_url = args.oagi_base_url or os.getenv("OAGI_BASE_URL", DEFAULT_BASE_URL)
    mode = args.mode or MODE_ACTOR
    screen = args.screen.strip("\"'") or "primary"
    step_delay = args.step_delay if args.step_delay is not None else DEFAULT_STEP_DELAY
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

    # Build agent kwargs - only pass explicitly provided values, let factory use defaults
    agent_kwargs = {
        "mode": mode,
        "api_key": api_key,
        "base_url": base_url,
        "step_observer": observer,
        "step_delay": step_delay,
    }
    if args.model:
        agent_kwargs["model"] = args.model
        # If thinker model specified without max_steps, use thinker's default
        if args.model == MODEL_THINKER and not args.max_steps:
            agent_kwargs["max_steps"] = DEFAULT_MAX_STEPS_THINKER
    if args.max_steps:
        agent_kwargs["max_steps"] = args.max_steps
    if args.temperature is not None:
        agent_kwargs["temperature"] = args.temperature

    # Create agent
    agent = create_agent(**agent_kwargs)

    # Create image provider
    image_provider = AsyncScreenshotMaker()

    # Create screen manager and get target screen info
    if screen:
        all_screens = screen_manager.get_all_screens()
        if screen not in all_screens:
            raise ValueError(
                f"Error: Screen '{screen}' not found. Available screens: {list(all_screens.keys())}"
            )
        target_screen = all_screens[screen]
        print(f"Target screen: {target_screen}")
        # Set the target screen for the image and action provider
        image_provider.set_target_screen(target_screen)
        action_handler.set_target_screen(target_screen)

    if args.instruction:
        print(f"Starting agent with instruction: {args.instruction}")
    else:
        print(f"Starting agent with mode: {mode} (using pre-configured instruction)")
    print(
        f"Mode: {mode}, Model: {agent.model}, Max steps: {agent.max_steps}, "
        f"Temperature: {agent.temperature}, Step delay: {step_delay}s"
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
