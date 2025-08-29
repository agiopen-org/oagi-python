# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
from datetime import date

from examples.execute_task_auto import execute_task_auto
from examples.execute_task_manual import execute_task_manual


def get_date():
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
    execute_task("Click where to and enter Foster City")
    execute_task(f"Click dates and click {start_date}")
    execute_task(f"Click {end_date} and hit search")


if __name__ == "__main__":
    main()
