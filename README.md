# OAGI Python SDK

Python SDK for the OAGI API - vision-based task automation.

## Installation

```bash
# Recommended: All features (desktop automation + server)
pip install oagi

# Or install core only (minimal dependencies)
pip install oagi-core

# Or install with specific features
pip install oagi-core[desktop]  # Desktop automation support
pip install oagi-core[server]   # Server support
```

**Requires Python >= 3.10**

### Installation Options

- **`oagi`** (Recommended): Metapackage that includes all features (desktop + server). Equivalent to `oagi-core[desktop,server]`.
- **`oagi-core`**: Core SDK with minimal dependencies (httpx, pydantic). Suitable for server deployments or custom automation setups.
- **`oagi-core[desktop]`**: Adds `pyautogui` and `pillow` for desktop automation features like screenshot capture and GUI control.
- **`oagi-core[server]`**: Adds FastAPI and Socket.IO dependencies for running the real-time server for browser extensions.

**Note**: Features requiring desktop dependencies (like `PILImage.from_screenshot()`, `PyautoguiActionHandler`, `ScreenshotMaker`) will show helpful error messages if you try to use them without installing the `desktop` extra.

## Quick Start

Set your API credentials:
```bash
export OAGI_API_KEY="your-api-key"
export OAGI_BASE_URL="https://api.oagi.com"  # or your server URL
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
```

### Async Support

Use async client for non-blocking operations and better concurrency:

```python
import asyncio
from oagi import AsyncShortTask

async def main():
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
- `screenshot_with_config.py` - Image compression and optimization
- `execute_task_auto.py` - Automated task execution
- `socketio_server_basic.py` - Socket.IO server example
- `socketio_client_example.py` - Socket.IO client implementation

## Socket.IO Server (Optional)

The SDK includes an optional Socket.IO server for real-time bidirectional communication with browser extensions or custom clients.

### Installation

```bash
# Install with server support
pip install oagi  # Includes server features
# Or
pip install oagi-core[server]  # Core + server only
```

### Running the Server

```python
import uvicorn
from oagi.server import create_app, ServerConfig

# Create FastAPI app with Socket.IO
app = create_app()

# Run server
uvicorn.run(app, host="0.0.0.0", port=8000)
```

Or use the example script:
```bash
export OAGI_API_KEY="your-api-key"
python examples/socketio_server_basic.py
```

### Server Features

- **Dynamic namespaces**: Each session gets its own namespace (`/session/{session_id}`)
- **Simplified events**: Single `init` event from client with instruction
- **Action execution**: Emit individual actions (click, type, scroll, etc.) to client
- **S3 integration**: Server sends presigned URLs for direct screenshot uploads
- **Session management**: In-memory session storage with timeout cleanup
- **REST API**: Health checks and session management endpoints

### Client Integration

Clients connect to a session namespace and handle action events:

```python
import socketio

sio = socketio.AsyncClient()
namespace = "/session/my_session_id"

@sio.on("request_screenshot", namespace=namespace)
async def on_screenshot(data):
    # Upload screenshot to S3 using presigned URL
    return {"success": True}

@sio.on("click", namespace=namespace)
async def on_click(data):
    # Execute click at coordinates
    return {"success": True}

await sio.connect("http://localhost:8000", namespaces=[namespace])
await sio.emit("init", {"instruction": "Click the button"}, namespace=namespace)
```

See [`examples/socketio_client_example.py`](examples/socketio_client_example.py) for a complete implementation.

## Documentation


## License

MIT