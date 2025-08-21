# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from .types import Action, ActionHandler, ActionType, Image, ImageProvider, Step


class ShortTask:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        # TODO: Initialize httpx client
        self.task_id = None

    def init_task(self, task_desc, max_steps=5):
        # TODO: Implement task initialization logic.
        pass

    def step(self, screenshot: Image) -> Step:
        # TODO: Send screenshot to the server and get the action.
        self.task_id = "..."
        result = Step(
            reason="Some mock reason.",
            actions=[Action(type=ActionType.CLICK, argument="...")],
            stop=False,
        )
        return result

    def auto_mode(
        self,
        task_desc,
        max_steps=5,
        executor: ActionHandler = None,
        image_provider: ImageProvider = None,
    ) -> bool:
        self.init_task(task_desc, max_steps=max_steps)

        for i in range(max_steps):
            image = image_provider()
            step = self.step(image)
            if step.stop:
                return True
            executor(step.actions)

        return False
