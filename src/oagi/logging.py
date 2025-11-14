# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import logging
import os


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name under the 'oagi' namespace.

    Log level is controlled by OAGI_LOG environment variable.
    Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
    Default: INFO
    """
    logger = logging.getLogger(f"oagi.{name}")
    oagi_root = logging.getLogger("oagi")

    # Get log level from environment
    log_level = os.getenv("OAGI_LOG", "INFO").upper()

    # Convert string to logging level
    try:
        level = getattr(logging, log_level)
    except AttributeError:
        level = logging.INFO

    # Configure root oagi logger once
    if not oagi_root.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        oagi_root.addHandler(handler)
        # Prevent propagation to root logger to avoid duplicate logs
        oagi_root.propagate = False

    # Always update level in case environment variable changed
    oagi_root.setLevel(level)

    # Suppress verbose httpx logs unless DEBUG level is enabled
    # httpx logs every HTTP request at INFO level by default
    httpx_logger = logging.getLogger("httpx")
    if level == logging.DEBUG:
        httpx_logger.setLevel(logging.DEBUG)
    else:
        httpx_logger.setLevel(logging.WARNING)

    return logger
