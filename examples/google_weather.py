# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from examples.execute_task_manual import execute_task_manual

is_completed, screenshot = execute_task_manual(
    desc := "Search weather with Google", max_steps=5
)

print(f"is_completed: {is_completed}, desc: {desc}")
