# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from .types import Image


class ScreenshotMaker:
    def __call__(self) -> Image:
        print("Taking screenshot")
        return Image()

    def last_image(self) -> Image:
        return Image()
