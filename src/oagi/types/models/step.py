# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from pydantic import BaseModel

from .action import Action


class Step(BaseModel):
    reason: str | None = None
    actions: list[Action]
    stop: bool = False
