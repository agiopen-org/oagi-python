# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from .types import Image


class FileImage:
    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()

    def read(self) -> bytes:
        return self.data


class MockImage:
    def read(self) -> bytes:
        return b"mock screenshot data"


class ScreenshotMaker:
    def __call__(self) -> Image:
        print("Taking screenshot")
        return MockImage()

    def last_image(self) -> Image:
        return MockImage()
