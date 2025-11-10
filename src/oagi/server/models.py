"""Pydantic models for Socket.IO events."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# Client-to-server events
class InitEventData(BaseModel):
    instruction: str = Field(...)
    model: Optional[str] = Field(default="vision-model-v1")
    temperature: Optional[float] = Field(default=0.0, ge=0.0, le=2.0)


# Server-to-client events
class BaseActionEventData(BaseModel):
    action_index: int = Field(..., ge=0)
    total_actions: int = Field(..., ge=1)


class ClickEventData(BaseActionEventData):
    x: int = Field(..., ge=0, le=1000)
    y: int = Field(..., ge=0, le=1000)
    click_type: Literal["single", "double", "triple", "right"] = Field(default="single")


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
    direction: Literal["up", "down", "left", "right"] = Field(...)
    count: int = Field(default=1, ge=1)


class WaitEventData(BaseActionEventData):
    duration_ms: int = Field(..., ge=0)


class FinishEventData(BaseActionEventData):
    pass


# Screenshot request/response
class ScreenshotRequestData(BaseModel):
    presigned_url: str = Field(...)
    uuid: str = Field(...)
    expires_at: str = Field(...)


class ScreenshotResponseData(BaseModel):
    success: bool = Field(...)
    error: Optional[str] = Field(None)


# Action acknowledgement
class ActionAckData(BaseModel):
    action_index: int = Field(...)
    success: bool = Field(...)
    error: Optional[str] = Field(None)
    execution_time_ms: Optional[int] = Field(None)


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
    code: Optional[str] = Field(None)
    details: Optional[dict] = Field(None)
