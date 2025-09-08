# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
from oagi import (
    AsyncPyautoguiActionHandler,
    AsyncScreenshotMaker,
    AsyncShortTask,
    PyautoguiActionHandler,
    ScreenshotMaker,
    ShortTask,
)


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


async def async_execute_task_auto(task_desc, max_steps=5):
    async with AsyncShortTask() as async_short_task:
        is_completed = await async_short_task.auto_mode(
            task_desc,
            max_steps=max_steps,
            executor=AsyncPyautoguiActionHandler(),
            image_provider=(sm := AsyncScreenshotMaker()),
        )

        return is_completed, await sm.last_image()
