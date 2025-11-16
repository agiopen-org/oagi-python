# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from typing import Literal

from pydantic import BaseModel, Field


# Client-to-server events
class InitEventData(BaseModel):
    instruction: str = Field(...)
    mode: str | None = Field(default="actor")
    model: str | None = Field(default="lux-v1")
    temperature: float | None = Field(default=0.1, ge=0.0, le=2.0)


# Server-to-client events
class BaseActionEventData(BaseModel):
    index: int = Field(..., ge=0)
    total: int = Field(..., ge=1)


class ClickEventData(BaseActionEventData):
    x: int = Field(..., ge=0, le=1000)
    y: int = Field(..., ge=0, le=1000)


class DragEventData(BaseActionEventData):
    x1: int = Field(..., ge=0, le=1000)
    y1: int = Field(..., ge=0, le=1000)
    x2: int = Field(..., ge=0, le=1000)
    y2: int = Field(..., ge=0, le=1000)


class HotkeyEventData(BaseActionEventData):
    combo: str = Field(...)
    count: int = Field(default=1, ge=1)


class TypeEventData(BaseActionEventData):
    text: str = Field(...)


class ScrollEventData(BaseActionEventData):
    x: int = Field(..., ge=0, le=1000)
    y: int = Field(..., ge=0, le=1000)
    direction: Literal["up", "down"] = Field(...)
    count: int = Field(default=1, ge=1)


class WaitEventData(BaseActionEventData):
    duration_ms: int = Field(default=1000, ge=0)


class FinishEventData(BaseActionEventData):
    pass


# Screenshot request/response
class ScreenshotRequestData(BaseModel):
    presigned_url: str = Field(...)
    uuid: str = Field(...)
    expires_at: str = Field(...)


class ScreenshotResponseData(BaseModel):
    success: bool = Field(...)
    error: str | None = Field(None)


# Action acknowledgement
class ActionAckData(BaseModel):
    index: int = Field(...)
    success: bool = Field(...)
    error: str | None = Field(None)
    execution_time_ms: int | None = Field(None)


# Session status
class SessionStatusData(BaseModel):
    session_id: str = Field(...)
    status: Literal["initialized", "running", "completed", "failed"] = Field(...)
    instruction: str = Field(...)
    created_at: str = Field(...)
    actions_executed: int = Field(default=0)
    last_activity: str = Field(...)


# Error event
class ErrorEventData(BaseModel):
    message: str = Field(...)
    code: str | None = Field(None)
    details: dict | None = Field(None)
