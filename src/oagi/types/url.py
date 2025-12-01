import re
from typing import NewType

URL = NewType("URL", str)

# Pattern to extract UUID from S3 URL
# Formats:
#   - https://bucket.s3.amazonaws.com/{user_id}/{uuid}.{ext}  (download URL)
#   - https://bucket.s3.amazonaws.com/{user_id}/{uuid}?...    (presigned URL)
_UUID_PATTERN = re.compile(
    r"/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:\.[a-z]+)?(?:\?|$)",
    re.IGNORECASE,
)


def extract_uuid_from_url(url: str) -> str | None:
    """Extract UUID from S3 URL.

    Args:
        url: S3 URL in one of these formats:
            - https://bucket.s3.amazonaws.com/{user_id}/{uuid}.jpg (download URL)
            - https://bucket.s3.amazonaws.com/{user_id}/{uuid}?... (presigned URL)

    Returns:
        UUID string if found, None otherwise
    """
    match = _UUID_PATTERN.search(url)
    return match.group(1) if match else None
