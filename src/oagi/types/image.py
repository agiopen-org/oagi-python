# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Protocol, runtime_checkable


@runtime_checkable
class Image(Protocol):
    """Protocol for image objects that can be read as bytes."""

    def read(self) -> bytes:
        """Read the image data as bytes."""
