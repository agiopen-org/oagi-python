# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import asyncio

from examples.execute_task_manual import async_execute_task_manual


async def main():
    is_completed, screenshot = await async_execute_task_manual(
        desc := "Search weather with Google", max_steps=5
    )

    print(f"is_completed: {is_completed}, desc: {desc}")


if __name__ == "__main__":
    asyncio.run(main())
