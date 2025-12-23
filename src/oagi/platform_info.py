# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

"""Platform information and SDK headers for analytics."""

import platform
import sys
from importlib.metadata import version

SDK_NAME = "oagi-python"


def get_sdk_version() -> str:
    """Get the SDK version from package metadata."""
    try:
        return version("oagi-core")
    except Exception:
        return "unknown"


def get_user_agent() -> str:
    """Build User-Agent string.

    Example: oagi-python/0.12.1 (python 3.11.5; darwin; arm64)
    """
    return (
        f"{SDK_NAME}/{get_sdk_version()} "
        f"(python {platform.python_version()}; {sys.platform}; {platform.machine()})"
    )


def get_sdk_headers() -> dict[str, str]:
    """Get SDK headers for API requests.

    Returns headers for both debugging (User-Agent) and structured analytics
    (x-sdk-* headers).
    """
    return {
        "User-Agent": get_user_agent(),
        "x-sdk-name": SDK_NAME,
        "x-sdk-version": get_sdk_version(),
        "x-sdk-language": "python",
        "x-sdk-language-version": platform.python_version(),
        "x-sdk-os": sys.platform,
        "x-sdk-platform": platform.machine(),
    }
