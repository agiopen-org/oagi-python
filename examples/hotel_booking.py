# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from oagi import ShortTask


def execute_task(task_desc, max_steps=5):
    short_task = ShortTask(api_key="your_api_key", base_url="your_base_url")
    short_task.init_task(task_desc, max_steps=max_steps)
    stop = False
    while not stop:
        # TODO: Take a screenshot
        screenshot = None  # Replace with actual screenshot logic
        actions = short_task.step(screenshot)
        # TODO: use pyautogui to execute the actions
        for func in actions['functions']:
            function_name = func['name']
            args = func['args']
            # TODO: Execute the function with args, e.g., pyautogui.click(args)
            print(f"Executing {function_name} with args {args}")
        stop = actions['stop']
    # TODO: Take a screenshot to check whether the task is completed
    screenshot = None  # Replace with actual screenshot logic
    is_completed = short_task.check_completion(screenshot)
    return is_completed, screenshot


def get_date():
    from datetime import date, timedelta
    today = date.today()
    # move to first day of this month
    first_day_this_month = today.replace(day=1)
    # move to first day of next month
    if first_day_this_month.month == 12:
        first_day_next_month = first_day_this_month.replace(year=first_day_this_month.year + 1, month=1)
    else:
        first_day_next_month = first_day_this_month.replace(month=first_day_this_month.month + 1)

    start_date = str(first_day_this_month)
    end_date = str(first_day_next_month.replace(day=3))
    return start_date, end_date


def main():

    """ Task decomposition
    1. Go to expedia.com
    2. Click where to and enter Foster City
    3. Click dates and click start date
    4. Click end date and hit search
    """
    start_date, end_date = get_date()
    is_completed, screenshot = execute_task("Go to expedia.com")
    is_completed, screenshot = execute_task(f"Click where to and enter Foster City")
    is_completed, screenshot = execute_task(f"Click dates and click {start_date}")
    is_completed, screenshot = execute_task(f"Click {end_date} and hit search")


if __name__ == "__main__":
    main()