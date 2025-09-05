# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ImageConfig(BaseModel):
    """Configuration for image capture and processing."""

    format: Literal["PNG", "JPEG"] = Field(
        default="JPEG", description="Image format for encoding"
    )
    quality: int = Field(
        default=85,
        ge=1,
        le=100,
        description="JPEG quality (1-100, only applies to JPEG format)",
    )
    width: int | None = Field(
        default=1260, description="Target width in pixels (will resize to exact size)"
    )
    height: int | None = Field(
        default=700, description="Target height in pixels (will resize to exact size)"
    )
    optimize: bool = Field(
        default=False,
        description="Enable PNG optimization (only applies to PNG format)",
    )
    resample: Literal["NEAREST", "BILINEAR", "BICUBIC", "LANCZOS"] = Field(
        default="LANCZOS", description="Resampling filter for resizing"
    )

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: int, info) -> int:
        """Validate quality parameter based on format."""
        values = info.data
        if values.get("format") == "PNG" and v != 85:
            return 85
        return v
