# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
from oagi import PyautoguiActionHandler, ScreenshotMaker, ShortTask


def execute_task_auto(task_desc, max_steps=5):
    # set OAGI_API_KEY and OAGI_BASE_URL
    # or ShortTask(api_key="your_api_key", base_url="your_base_url")
    short_task = ShortTask()

    is_completed = short_task.auto_mode(
        task_desc,
        max_steps=max_steps,
        executor=PyautoguiActionHandler(),  # or executor = lambda actions: print(actions) for debugging
        image_provider=(sm := ScreenshotMaker()),
    )

    return is_completed, sm.last_image()
