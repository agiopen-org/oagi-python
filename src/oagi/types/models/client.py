# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from pydantic import BaseModel

from .action import Action


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


class LLMResponse(BaseModel):
    id: str
    task_id: str
    object: str = "task.completion"
    created: int
    model: str
    task_description: str
    current_step: int
    is_complete: bool
    actions: list[Action]
    reason: str | None = None
    usage: Usage
    error: ErrorDetail | None = None
