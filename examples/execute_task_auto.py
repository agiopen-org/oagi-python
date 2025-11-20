# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
import asyncio

from oagi import (
    AsyncDefaultAgent,
    AsyncPyautoguiActionHandler,
    AsyncScreenshotMaker,
)


def execute_task_auto(task_desc, max_steps=5):
    """Synchronous wrapper for async task execution."""
    return asyncio.run(async_execute_task_auto(task_desc, max_steps))


async def async_execute_task_auto(task_desc, max_steps=5):
    # set OAGI_API_KEY and OAGI_BASE_URL
    # or AsyncDefaultAgent(api_key="your_api_key", base_url="your_base_url")
    agent = AsyncDefaultAgent(max_steps=max_steps)

    # executor = lambda actions: print(actions) for debugging
    action_handler = AsyncPyautoguiActionHandler()
    image_provider = AsyncScreenshotMaker()

    is_completed = await agent.execute(
        task_desc,
        action_handler=action_handler,
        image_provider=image_provider,
    )

    return is_completed, await image_provider.last_image()
