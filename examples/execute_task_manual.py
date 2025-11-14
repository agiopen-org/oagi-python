# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from oagi import (
    Actor,
    AsyncActor,
    AsyncPyautoguiActionHandler,
    AsyncScreenshotMaker,
    PyautoguiActionHandler,
    ScreenshotMaker,
)


def execute_task_manual(task_desc, max_steps=5):
    # set OAGI_API_KEY and OAGI_BASE_URL
    # or Actor(api_key="your_api_key", base_url="your_base_url")
    actor = Actor()
    actor.init_task(task_desc, max_steps=max_steps)
    executor = (
        PyautoguiActionHandler()
    )  # executor = lambda actions: print(actions) for debugging

    # by default, screenshot will be resized to 1260 * 700 and jpeg with quality 85
    # for best image quality, use ScreenshotMaker(config=ImageConfig(format="PNG"))
    image_provider = ScreenshotMaker()

    for i in range(max_steps):
        # image can also be bytes
        # with open("test_screenshot.png", "rb") as f:
        #     image = f.read()
        image = image_provider()

        # For additional instructions
        # step = actor.step(image, instruction="some instruction")
        step = actor.step(image)

        # do something with step, maybe print to debug
        print(f"Step {i}: {step.reason=}")

        if step.stop:
            print(f"Task completed after {i} steps.")
            is_completed = True
            screenshot = image_provider.last_image()
            break

        executor(step.actions)
    else:
        # If we didn't break out of the loop, we used up all our steps
        is_completed = False
        screenshot = image_provider()

    print(f"manual execution completed: {is_completed=}, {task_desc=}\n")
    return is_completed, screenshot


async def async_execute_task_manual(task_desc, max_steps=5):
    # set OAGI_API_KEY and OAGI_BASE_URL
    # or AsyncActor(api_key="your_api_key", base_url="your_base_url")
    async with AsyncActor() as actor:
        await actor.init_task(task_desc, max_steps=max_steps)
        executor = AsyncPyautoguiActionHandler()

        # by default, screenshot will be resized to 1260 * 700 and jpeg with quality 85
        # for best image quality, use ScreenshotMaker(config=ImageConfig(format="PNG"))
        image_provider = AsyncScreenshotMaker()

        for i in range(max_steps):
            # image can also be bytes
            # with open("test_screenshot.png", "rb") as f:
            #     image = f.read()
            image = await image_provider()

            # For additional instructions
            # step = actor.step(image, instruction="some instruction")
            step = await actor.step(image)

            # do something with step, maybe print to debug
            print(f"Step {i}: {step.reason=}")

            if step.stop:
                print(f"Task completed after {i} steps.")
                is_completed = True
                screenshot = await image_provider.last_image()
                break

            await executor(step.actions)
        else:
            # If we didn't break out of the loop, we used up all our steps
            is_completed = False
            screenshot = await image_provider()

        print(f"manual execution completed: {is_completed=}, {task_desc=}\n")
        return is_completed, screenshot
