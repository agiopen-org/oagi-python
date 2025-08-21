# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from .types import Image


class MockImage:
    """Mock image implementation for testing/stub purposes."""

    def read(self) -> bytes:
        return b"mock screenshot data"


class ScreenshotMaker:
    def __call__(self) -> Image:
        print("Taking screenshot")
        return MockImage()

    def last_image(self) -> Image:
        return MockImage()
