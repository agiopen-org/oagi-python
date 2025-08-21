# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from oagi import PyautoguiActionHandler, ScreenshotMaker, ShortTask


def execute_task_auto(task_desc, max_steps=5):
    short_task = ShortTask(api_key="your_api_key", base_url="your_base_url")

    is_completed = short_task.auto_mode(
        task_desc,
        max_steps=max_steps,
        executor=PyautoguiActionHandler(),  # or executor = lambda actions: print(actions) for debugging
        image_provider=(ls := ScreenshotMaker()),
    )

    return is_completed, ls.last_image()


def execute_task_manual(task_desc, max_steps=5):
    short_task = ShortTask(api_key="your_api_key", base_url="your_base_url")
    short_task.init_task(task_desc, max_steps=max_steps)
    executor = PyautoguiActionHandler()  # executor = OutputExecutor()
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


def get_date():
    from datetime import date

    today = date.today()
    # move to first day of this month
    first_day_this_month = today.replace(day=1)
    # move to first day of next month
    if first_day_this_month.month == 12:
        first_day_next_month = first_day_this_month.replace(
            year=first_day_this_month.year + 1, month=1
        )
    else:
        first_day_next_month = first_day_this_month.replace(
            month=first_day_this_month.month + 1
        )

    start_date = str(first_day_this_month)
    end_date = str(first_day_next_month.replace(day=3))
    return start_date, end_date


def main():
    """Task decomposition
    1. Go to expedia.com
    2. Click where to and enter Foster City
    3. Click dates and click start date
    4. Click end date and hit search
    """
    start_date, end_date = get_date()

    is_completed, screenshot = execute_task_auto(desc := "Go to expedia.com")
    print(f"auto execution completed: {is_completed=}, {desc=}\n")

    execute_task = execute_task_manual  # or execute_task_auto
    is_completed, screenshot = execute_task("Click where to and enter Foster City")
    is_completed, screenshot = execute_task(f"Click dates and click {start_date}")
    is_completed, screenshot = execute_task(f"Click {end_date} and hit search")


if __name__ == "__main__":
    main()
