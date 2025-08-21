# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Protocol

from .image import Image


class ImageProvider(Protocol):
    def __call__(self) -> Image:
        """
        Represents the functionality to invoke the callable object and produce an Image
        result. Typically used to process or generate images using the defined logic
        within the __call__ method.

        Returns:
            Image: The resulting image output from the callable logic.
        """

    def last_image(self) -> Image:
        """
        Returns the last captured image.

        This method retrieves the most recent image that was captured and stored
        in memory. If there are no images available, the method may return None.

        Returns:
            Image: The last captured image, or None if no images are available.
        """
