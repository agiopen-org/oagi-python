# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import argparse
import sys

from oagi.cli.agent import add_agent_parser, handle_agent_command
from oagi.cli.server import add_server_parser, handle_server_command
from oagi.cli.utils import display_config, display_version, setup_logging


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oagi", description="OAGI SDK Command Line Interface"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose (debug) logging"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (use 'oagi version' for detailed info)",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_server_parser(subparsers)
    add_agent_parser(subparsers)

    subparsers.add_parser("version", help="Show SDK version and environment info")

    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", required=True
    )
    config_subparsers.add_parser("show", help="Display current configuration")

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        if args.command == "server":
            handle_server_command(args)
        elif args.command == "agent":
            handle_agent_command(args)
        elif args.command == "version":
            display_version()
        elif args.command == "config":
            if args.config_command == "show":
                display_config()
        else:
            parser.print_help()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
