# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from oagi import PyautoguiActionHandler, ScreenshotMaker, ShortTask


def execute_task_manual(task_desc, max_steps=5):
    # set OAGI_API_KEY and OAGI_BASE_URL
    # or ShortTask(api_key="your_api_key", base_url="your_base_url")
    short_task = ShortTask()
    short_task.init_task(task_desc, max_steps=max_steps)
    executor = (
        PyautoguiActionHandler()
    )  # executor = lambda actions: print(actions) for debugging
    image_provider = ScreenshotMaker()

    for i in range(max_steps):
        image = image_provider()
        # do something with image, maybe save it or OCR then break
        step = short_task.step(image)
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
