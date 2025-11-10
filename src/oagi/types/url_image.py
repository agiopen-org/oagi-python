"""URLImage implementation for handling images via URLs."""

from typing import Optional


class URLImage:
    """Image implementation that supports URLs.

    This is useful when the image is already uploaded to a URL (e.g., S3)
    and we want to pass the URL reference instead of downloading bytes.
    """

    def __init__(self, url: str, cached_bytes: Optional[bytes] = None):
        """Initialize URLImage with a URL.

        Args:
            url: URL of the image
            cached_bytes: Optional cached bytes of the image
        """
        self.url = url
        self._cached_bytes = cached_bytes

    def read(self) -> bytes:
        """Read the image data as bytes.

        For URL-based images, this returns empty bytes by default since
        the image is already uploaded. Subclasses can override to fetch
        the actual bytes from the URL if needed.

        Returns:
            Image bytes (empty for URL-only images)
        """
        if self._cached_bytes is not None:
            return self._cached_bytes
        return b""

    def get_url(self) -> str:
        """Get the URL of the image.

        Returns:
            The image URL
        """
        return self.url

    def __repr__(self) -> str:
        """String representation of URLImage."""
        return f"URLImage(url='{self.url}')"
