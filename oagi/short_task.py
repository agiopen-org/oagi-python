# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------


class ShortTask:

    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        # TODO: Initialize websocket connection. Get task id.
        self.task_id = None
        return self.task_id

    def init_task(self, task_desc, max_steps=5):
        # TODO: Implement task initialization logic.
        pass

    def step(self, screenshot):
        # TODO: Send screenshot to the server and get the action.
        actions = {
            "reason": "...",
            "functions": [
                {"name": "...", "args": "..."}
            ],
            "stop": False, # or True
        }
        return actions

    def check_completion(self, screenshot):
        # TODO: We will have a model to check whether the task is completed
        return True # or False
