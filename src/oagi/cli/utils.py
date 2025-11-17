# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import logging
import os
import sys
from importlib.metadata import version as get_version

from oagi.exceptions import check_optional_dependency


def get_sdk_version() -> str:
    # Try oagi-core first (development install), then oagi (metapackage install)
    for package_name in ["oagi-core", "oagi"]:
        try:
            version = get_version(package_name)
            # Skip if version is 0.0.0 (placeholder/invalid)
            if version != "0.0.0":
                return version
        except Exception:
            continue
    return "unknown"


def display_version() -> None:
    sdk_version = get_sdk_version()
    python_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    platform = sys.platform

    print(f"OAGI SDK version: {sdk_version}")
    print(f"Python version: {python_version}")
    print(f"Platform: {platform}")

    # Check installed extras
    extras = []
    if check_optional_dependency("pyautogui", "Desktop", "desktop", raise_error=False):
        extras.append("desktop")

    if check_optional_dependency("fastapi", "Server", "server", raise_error=False):
        extras.append("server")

    if extras:
        print(f"Installed extras: {', '.join(extras)}")
    else:
        print("Installed extras: none")


def display_config() -> None:
    config_vars = {
        "OAGI_API_KEY": os.getenv("OAGI_API_KEY", ""),
        "OAGI_BASE_URL": os.getenv("OAGI_BASE_URL", "https://api.agiopen.org"),
        "OAGI_DEFAULT_MODEL": os.getenv("OAGI_DEFAULT_MODEL", "lux-actor-1"),
        "OAGI_LOG_LEVEL": os.getenv("OAGI_LOG_LEVEL", "INFO"),
        "OAGI_SERVER_HOST": os.getenv("OAGI_SERVER_HOST", "0.0.0.0"),
        "OAGI_SERVER_PORT": os.getenv("OAGI_SERVER_PORT", "8000"),
        "OAGI_MAX_STEPS": os.getenv("OAGI_MAX_STEPS", "30"),
    }

    print("Current Configuration:")
    print("-" * 50)
    for key, value in config_vars.items():
        if key == "OAGI_API_KEY" and value:
            # Mask API key
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print(f"{key}: {masked}")
        else:
            display_value = value if value else "(not set)"
            print(f"{key}: {display_value}")


def setup_logging(verbose: bool) -> None:
    if verbose:
        os.environ["OAGI_LOG_LEVEL"] = "DEBUG"
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        log_level = os.getenv("OAGI_LOG_LEVEL", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level), format="%(levelname)s: %(message)s"
        )
