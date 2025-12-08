# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from pydantic import BaseModel, Field


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorDetail | None


class UploadFileResponse(BaseModel):
    """Response from S3 presigned URL upload."""

    url: str
    uuid: str
    expires_at: int
    file_expires_at: int
    download_url: str


class GenerateResponse(BaseModel):
    """Response from /v1/generate endpoint."""

    response: str
    prompt_tokens: int
    completion_tokens: int
    cost: float | None = Field(
        default=None,
        deprecated=True,
        description="This field is deprecated",
    )
