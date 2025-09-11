# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CLICK = "click"
    LEFT_DOUBLE = "left_double"
    LEFT_TRIPLE = "left_triple"
    RIGHT_SINGLE = "right_single"
    DRAG = "drag"
    HOTKEY = "hotkey"
    TYPE = "type"
    SCROLL = "scroll"
    FINISH = "finish"
    WAIT = "wait"
    CALL_USER = "call_user"


class Action(BaseModel):
    type: ActionType = Field(..., description="Type of action to perform")
    argument: str = Field(..., description="Action argument in the specified format")
    count: int | None = Field(
        default=1, ge=1, description="Number of times to repeat the action"
    )
