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

from oagi.exceptions import check_optional_dependency


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
    run_parser.add_argument("--model", type=str, help="Model to use (default: lux-v1)")
    run_parser.add_argument(
        "--max-steps", type=int, help="Maximum number of steps (default: 30)"
    )
    run_parser.add_argument(
        "--temperature", type=float, help="Sampling temperature (default: 0.0)"
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
    model = args.model or "lux-v1"
    max_steps = args.max_steps or 30
    temperature = args.temperature if args.temperature is not None else 0.0
    mode = args.mode or "actor"

    # Create agent
    agent = create_agent(
        mode=mode,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_steps=max_steps,
        temperature=temperature,
    )

    # Create handlers
    action_handler = AsyncPyautoguiActionHandler()
    image_provider = AsyncScreenshotMaker()

    print(f"Starting agent with instruction: {args.instruction}")
    print(
        f"Mode: {mode}, Model: {model}, Max steps: {max_steps}, Temperature: {temperature}"
    )
    print("-" * 60)

    # Run agent
    try:
        success = asyncio.run(
            agent.execute(
                instruction=args.instruction,
                action_handler=action_handler,
                image_provider=image_provider,
            )
        )

        print("-" * 60)
        if success:
            print("Task completed successfully!")
            sys.exit(0)
        else:
            print("Task failed or reached max steps without completion.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nAgent execution interrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"Error during agent execution: {e}", file=sys.stderr)
        sys.exit(1)
