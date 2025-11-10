"""Tests for URLImage implementation."""

from oagi.types import URLImage


class TestURLImage:
    def test_url_image_creation(self):
        url = "https://example.com/image.png"
        image = URLImage(url)

        assert image.url == url
        assert image.get_url() == url

    def test_url_image_read_empty_bytes(self):
        url = "https://example.com/image.png"
        image = URLImage(url)

        data = image.read()
        assert data == b""

    def test_url_image_with_cached_bytes(self):
        url = "https://example.com/image.png"
        cached_data = b"cached image data"
        image = URLImage(url, cached_bytes=cached_data)

        data = image.read()
        assert data == cached_data

    def test_url_image_repr(self):
        url = "https://example.com/image.png"
        image = URLImage(url)

        assert repr(image) == f"URLImage(url='{url}')"

    def test_url_image_protocol_compliance(self):
        url = "https://example.com/image.png"
        image = URLImage(url)

        # URLImage should implement the Image protocol
        assert hasattr(image, "read")
        assert callable(image.read)
