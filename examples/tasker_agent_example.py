# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import asyncio
import os
import traceback

from oagi import (
    AsyncAgentObserver,
    AsyncPyautoguiActionHandler,
    AsyncScreenshotMaker,
    TaskerAgent,
)


async def main():
    # Create observer for recording execution history
    observer = AsyncAgentObserver()

    # Initialize the tasker agent
    # Note: Ensure OAGI_API_KEY and OAGI_BASE_URL environment variables are set
    tasker = TaskerAgent(
        api_key=os.getenv("OAGI_API_KEY"),
        base_url=os.getenv("OAGI_BASE_URL", "https://api.agiopen.org"),
        model="sft-bigs1-1027-s2-1113-mixoc-1107-32b",
        max_steps=30,
        temperature=0.5,
        step_observer=observer,
    )

    # Define the task with multiple todos
    task_description = "Open a web browser and search for information about Python"

    # Break down into specific todos
    todos = [
        "Search for 'Python programming language'",
        "Click on the official Python.org website link",
    ]

    # Set the task
    tasker.set_task(
        task=task_description,
        todos=todos,
    )

    image_provider = AsyncScreenshotMaker()
    action_handler = AsyncPyautoguiActionHandler()

    try:
        # Execute the task
        success = await tasker.execute(
            instruction="",
            action_handler=action_handler,
            image_provider=image_provider,
        )
        print(f"Tasker success: {success}")

    except Exception as e:
        print(f"\nError during execution: {e}")
        traceback.print_exc()

    observer.export("html", export_file := "export.html")
    print(f"\nExecution history exported: {export_file}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
