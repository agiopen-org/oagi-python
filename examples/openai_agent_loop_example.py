# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------
"""
Example: OpenAI-Compatible Agent Loop

This example demonstrates how to build an agent loop using:
1. OAGI file upload for screenshots
2. OAGI action handler for execution
3. OAGI utilities for prompt building and action parsing
4. OpenAI-compatible API endpoint for LLM calls

Environment variables:
- OAGI_API_KEY: Your OAGI API key
- OAGI_BASE_URL: API base URL (default: https://api.agiopen.org)
"""

import os

from openai import OpenAI

from oagi import PyautoguiActionHandler, ScreenshotMaker, SyncClient
from oagi.utils.output_parser import parse_raw_output
from oagi.utils.prompt_builder import build_prompt

DEFAULT_BASE_URL = "https://api.agiopen.org"
DEFAULT_MODEL = "lux-thinker-1"


def agent_loop(task_description: str, max_steps: int = 100) -> bool:
    """
    Run an agent loop to complete a task.

    Args:
        task_description: The task to complete
        max_steps: Maximum number of steps to take

    Returns:
        True if task completed, False if max steps reached
    """
    # Get configuration from environment
    api_key = os.environ.get("OAGI_API_KEY")
    base_url = os.environ.get("OAGI_BASE_URL", DEFAULT_BASE_URL)

    if not api_key:
        raise ValueError("OAGI_API_KEY environment variable is required")

    # Initialize clients and handlers
    oagi_client = SyncClient(api_key=api_key, base_url=base_url)
    openai_client = OpenAI(api_key=api_key, base_url=f"{base_url}/v1")
    action_handler = PyautoguiActionHandler()
    image_provider = ScreenshotMaker()

    messages: list[dict] = []

    print(f"Starting task: {task_description}")
    print(f"Max steps: {max_steps}")
    print("-" * 50)

    try:
        for step_num in range(max_steps):
            # 1. Capture screenshot
            screenshot = image_provider()

            # 2. Upload to S3
            upload_resp = oagi_client.put_s3_presigned_url(screenshot)
            screenshot_url = upload_resp.download_url

            # 3. Build message (with prompt on first step)
            content = []
            if step_num == 0:
                content.append({"type": "text", "text": build_prompt(task_description)})
            content.append({"type": "image_url", "image_url": {"url": screenshot_url}})
            messages.append({"role": "user", "content": content})

            # 4. Call OpenAI-compatible API
            response = openai_client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
            )
            raw_output = response.choices[0].message.content or ""

            # 5. Add assistant message to history
            messages.append({"role": "assistant", "content": raw_output})

            # 6. Parse output using oagi utility
            step = parse_raw_output(raw_output)
            print(f"Step {step_num}: {step.reason}")
            print(f"  Actions: {step.actions}")

            # 7. Check for completion
            if step.stop:
                print("-" * 50)
                print("Task completed!")
                return True

            # 8. Execute actions
            action_handler(step.actions)

        print("-" * 50)
        print("Max steps reached without completion")
        return False

    finally:
        oagi_client.close()
        openai_client.close()


if __name__ == "__main__":
    # Example task
    task = "Find some shoes on amazon"

    success = agent_loop(task, max_steps=100)
    print(f"\nFinal result: {'Success' if success else 'Failed'}")
