# OAGI Python SDK

## Basic Usage
```bash
pip install oagi # python >= 3.10
```
```bash
export OAGI_BASE_URL=""
export OAGI_API_KEY="sk-xxxx"
```

```python
from oagi import PyautoguiActionHandler, ScreenshotMaker, ShortTask
short_task = ShortTask()
is_completed = short_task.auto_mode(
    "Search weather with Google",
    max_steps=5,
    executor=PyautoguiActionHandler(),
    image_provider=(sm := ScreenshotMaker()),
)
```