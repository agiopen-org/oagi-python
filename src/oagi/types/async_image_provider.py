# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Protocol

from .image import Image


class AsyncImageProvider(Protocol):
    async def __call__(self) -> Image:
        """
        Asynchronously provides an image.

        This method is responsible for asynchronously capturing, generating, or retrieving
        an image that can be used for task execution or analysis. The method should return
        an object that implements the Image protocol.

        Returns:
            Image: An object implementing the Image protocol that represents
                  the captured or generated image.

        Raises:
            RuntimeError: If an error occurs during image capture or generation.
        """

    async def last_image(self) -> Image:
        """
        Asynchronously returns the last captured image.

        Returns:
            Image: The last captured image.
        """
