# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

"""Deprecated: Use oagi.actor instead. This module will be removed in a future version."""

import warnings

from oagi.actor import (
    Actor,
    AsyncActor,
    AsyncShortTask,
    AsyncTask,
    ShortTask,
    Task,
)

warnings.warn(
    "oagi.task is deprecated, use oagi.actor instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "Actor",
    "AsyncActor",
    "Task",
    "AsyncTask",
    "ShortTask",
    "AsyncShortTask",
]
