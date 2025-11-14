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


def handle_agent_command(args: argparse.Namespace) -> None:
    if args.agent_command == "run":
        run_agent(args)


def run_agent(args: argparse.Namespace) -> None:
    # Check if desktop extras are installed
    check_optional_dependency("pyautogui", "Agent execution", "desktop")
    check_optional_dependency("PIL", "Agent execution", "desktop")

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

    # Create step tracker
    step_tracker = StepTracker()

    # Create agent with step tracker
    agent = create_agent(
        mode=mode,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
        step_observer=step_tracker,
    )

    # Create handlers
    action_handler = AsyncPyautoguiActionHandler()
    image_provider = AsyncScreenshotMaker()

    print(f"Starting agent with instruction: {args.instruction}")
    print(
        f"Mode: {mode}, Model: {model}, Max steps: {max_steps}, Temperature: {temperature}"
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

        if interrupted:
            sys.exit(130)
        elif not success:
            sys.exit(1)
