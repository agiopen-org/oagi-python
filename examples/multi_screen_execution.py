# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
import asyncio
import sys

from oagi import ScreenManager

# Must be initialized before importing pyautogui to ensure correct DPI awareness in Windows
if sys.platform == "win32":
    ScreenManager.enable_windows_dpi_awareness()

from oagi import (
    AsyncDefaultAgent,
    AsyncPyautoguiActionHandler,
    AsyncScreenshotMaker,
)


def print_all_screens():
    """Print all available screens."""
    screen_manager = ScreenManager()
    all_screens = screen_manager.get_all_screens()
    print("Available screens:")
    for screen_index, screen in enumerate(all_screens):
        print(f"  - Index {screen_index}: {screen}")
    return


def execute_task_on_specific_screen(task_desc, max_steps=5, screen_index=0):
    """Synchronous wrapper for async task execution."""
    # Print all screens and choose one screen for task exection
    return asyncio.run(
        async_execute_task_on_specific_screen(task_desc, max_steps, screen_index)
    )


async def async_execute_task_on_specific_screen(task_desc, max_steps=5, screen_index=0):
    # set OAGI_API_KEY and OAGI_BASE_URL
    # or AsyncDefaultAgent(api_key="your_api_key", base_url="your_base_url")
    agent = AsyncDefaultAgent(max_steps=max_steps)

    # executor = lambda actions: print(actions) for debugging
    action_handler = AsyncPyautoguiActionHandler()
    image_provider = AsyncScreenshotMaker()

    # Get the target screen info for task exection
    screen_manager = ScreenManager()
    all_screens = screen_manager.get_all_screens()
    screen = all_screens[screen_index]
    # Set the screen index for handlers
    action_handler.set_target_screen(screen)
    image_provider.set_target_screen(screen)

    is_completed = await agent.execute(
        task_desc,
        action_handler=action_handler,
        image_provider=image_provider,
    )

    return is_completed, await image_provider.last_image()


if __name__ == "__main__":
    # Example task
    task_desc = "Open Chrome and navigate to google.com"
    screen_index = 1  # Use the second screen as example
    success, image = execute_task_on_specific_screen(
        task_desc, screen_index=screen_index
    )
    print(f"\nFinal result: {'Success' if success else 'Failed'}")
