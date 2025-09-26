# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from oagi import ScreenshotMaker, ShortTask


def main():
    # First session - start a new task
    print("=== First Session ===")
    task1 = ShortTask()
    task1.init_task("Open calculator app")

    image_provider = ScreenshotMaker()

    # Execute a few steps in the first session
    for i in range(1):
        image = image_provider()
        step = task1.step(image)
        print(f"Session 1, Step {i + 1}: {step.reason}, Actions: {step.actions}")

        if step.stop:
            break

    # Save the task_id from the first session
    previous_task_id = task1.task_id
    print(f"\nFirst session task_id: {previous_task_id}")

    # Second session - continue with context from the first session
    print("\n=== Second Session (with history) ===")
    task2 = ShortTask()
    task2.init_task("Calculate 25 * 4", last_task_id=previous_task_id, history_steps=1)

    # Execute steps with history context
    for i in range(3):
        image = image_provider()
        step = task2.step(image)
        print(f"Session 2, Step {i + 1}: {step.reason}, Actions: {step.actions}")

        if step.stop:
            print("✓ Task completed!")
            break

    print(f"\nSecond session task_id: {task2.task_id}")
    print(f"Used history from: {task2.last_task_id}")


if __name__ == "__main__":
    main()
