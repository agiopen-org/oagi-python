# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import argparse
import sys

from oagi.exceptions import check_optional_dependency


def add_server_parser(subparsers: argparse._SubParsersAction) -> None:
    server_parser = subparsers.add_parser("server", help="Server management commands")
    server_subparsers = server_parser.add_subparsers(
        dest="server_command", required=True
    )

    # server start command
    start_parser = server_subparsers.add_parser(
        "start", help="Start the Socket.IO server"
    )
    start_parser.add_argument(
        "--host",
        type=str,
        help="Server host (default: 0.0.0.0, or OAGI_SERVER_HOST env var)",
    )
    start_parser.add_argument(
        "--port",
        type=int,
        help="Server port (default: 8000, or OAGI_SERVER_PORT env var)",
    )
    start_parser.add_argument(
        "--oagi-api-key", type=str, help="OAGI API key (default: OAGI_API_KEY env var)"
    )
    start_parser.add_argument(
        "--oagi-base-url",
        type=str,
        help="OAGI base URL (default: https://api.agiopen.org, or OAGI_BASE_URL env var)",
    )


def handle_server_command(args: argparse.Namespace) -> None:
    if args.server_command == "start":
        start_server(args)


def start_server(args: argparse.Namespace) -> None:
    # Check if server extras are installed
    check_optional_dependency("fastapi", "Server", "server")
    check_optional_dependency("uvicorn", "Server", "server")

    import uvicorn  # noqa: PLC0415

    from oagi.server import create_app  # noqa: PLC0415
    from oagi.server.config import ServerConfig  # noqa: PLC0415

    # Create config with CLI overrides
    config_kwargs = {}
    if args.oagi_api_key:
        config_kwargs["oagi_api_key"] = args.oagi_api_key
    if args.oagi_base_url:
        config_kwargs["oagi_base_url"] = args.oagi_base_url
    if args.host:
        config_kwargs["server_host"] = args.host
    if args.port:
        config_kwargs["server_port"] = args.port

    try:
        config = ServerConfig(**config_kwargs)
    except Exception as e:
        print(f"Error: Invalid configuration - {e}", file=sys.stderr)
        sys.exit(1)

    # Create and run app
    print(
        f"Starting OAGI Socket.IO server on {config.server_host}:{config.server_port}"
    )
    print(f"OAGI API: {config.oagi_base_url}")
    print(f"Model: {config.default_model}")
    print("\nPress Ctrl+C to stop the server")

    try:
        app = create_app(config)
        uvicorn.run(
            app, host=config.server_host, port=config.server_port, log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)
