# OAGI Python SDK

Python SDK for the OAGI API - vision-based task automation.

## Installation

```bash
pip install oagi  # requires Python >= 3.10
```

## Quick Start

Set your API credentials:
```bash
export OAGI_API_KEY="your-api-key"
export OAGI_BASE_URL="https://api.oagi.com"  # or your server URL
```

### Single-Step Analysis

Analyze a screenshot and get recommended actions:

```python
from oagi import single_step

step = single_step(
    task_description="Click the submit button",
    screenshot="screenshot.png"  # or bytes, or Image object
)

print(f"Actions: {step.actions}")
print(f"Complete: {step.is_complete}")
```

### Automated Task Execution

Run tasks automatically with screenshot capture and action execution:

```python
from oagi import ShortTask, ScreenshotMaker, PyautoguiActionHandler

task = ShortTask()
completed = task.auto_mode(
    "Search weather on Google",
    max_steps=10,
    executor=PyautoguiActionHandler(),  # Executes mouse/keyboard actions
    image_provider=ScreenshotMaker(),    # Captures screenshots
)
```

Configure PyAutoGUI behavior with custom settings:

```python
from oagi import PyautoguiActionHandler, PyautoguiConfig

# Customize action behavior
config = PyautoguiConfig(
    drag_duration=1.0,      # Slower drags for precision (default: 0.5)
    scroll_amount=50,       # Larger scroll steps (default: 30)
    wait_duration=2.0,      # Longer waits (default: 1.0)
    action_pause=0.2,       # More pause between actions (default: 0.1)
    hotkey_interval=0.1,    # Interval between keys in hotkey combinations (default: 0.1)
    capslock_mode="session" # Caps lock mode: 'session' or 'system' (default: 'session')
)

executor = PyautoguiActionHandler(config=config)
task.auto_mode("Complete form", executor=executor, image_provider=ScreenshotMaker())
```

### Image Processing

Process and optimize images before sending to API:

```python
from oagi import PILImage, ImageConfig

# Load and compress an image
image = PILImage.from_file("large_screenshot.png")
config = ImageConfig(
    format="JPEG",
    quality=85,
    width=1260,
    height=700
)
compressed = image.transform(config)

# Use with single_step
step = single_step("Click button", screenshot=compressed)
```

### Async Support

Use async client for non-blocking operations and better concurrency:

```python
import asyncio
from oagi import async_single_step, AsyncShortTask

async def main():
    # Single-step async analysis
    step = await async_single_step(
        "Find the search bar",
        screenshot="screenshot.png"
    )
    print(f"Found {len(step.actions)} actions")
    
    # Async task automation
    task = AsyncShortTask()
    async with task:
        await task.init_task("Complete the form")
        # ... continue with async operations

asyncio.run(main())
```

## Examples

See the [`examples/`](examples/) directory for more usage patterns:
- `google_weather.py` - Basic task execution with `ShortTask`
- `single_step.py` - Basic single-step inference
- `screenshot_with_config.py` - Image compression and optimization
- `execute_task_auto.py` - Automated task execution

## Documentation


## License

MIT