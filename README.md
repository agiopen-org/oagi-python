# OAGI Python SDK

[![PyPI version](https://img.shields.io/pypi/v/oagi-core)](https://pypi.org/project/oagi-core/)
[![Python version](https://img.shields.io/pypi/pyversions/oagi-core)](https://pypi.org/project/oagi-core/)
[![License](https://img.shields.io/github/license/agiopen-org/oagi-python)](https://github.com/agiopen-org/oagi-python/blob/main/LICENSE)
[![Build status](https://img.shields.io/github/actions/workflow/status/agiopen-org/oagi-python/ci.yml?branch=main)](https://github.com/agiopen-org/oagi-python/actions/workflows/ci.yml)

Python SDK for the OAGI API - vision-based task automation.

## What is OAGI?

OAGI is the Python SDK for **Lux**, the world's most advanced computer-use model from the OpenAGI Foundation. 

**Computer Use** is AI's ability to operate human-facing software — not just through APIs, but by operating computers natively, just as human users do. It's a paradigm shift in what AI can do: not just generating, reasoning, or researching, but actually operating on your computer.

Lux comes in three modes, giving you control over depth, speed, and style of execution:

- **Tasker** — Strictly follows step-by-step instructions with ultra-stable, controllable execution
- **Actor** — Ideal for immediate tasks, completing actions at near-instant speed
- **Thinker** — Understands vague, complex goals, performing hour-long executions

### Use Cases

With Lux, possibilities are endless. Here are a few examples:

- **Web Scraping & Data Crawl** — Navigate websites, sort results, and collect product information autonomously
- **Software QA** — Automate repetitive testing tasks, navigate applications, perform test actions, and validate expected behaviors
- **Financial Data Extraction** — Navigate to sites like NASDAQ and extract insider activity data
- **Data Entry** — Enter accurate data across dashboards and forms
- **Workflow Automation** — Chain together multi-step tasks across different applications

## Table of Contents

- [What is OAGI?](#what-is-oagi)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Automated Task Execution](#automated-task-execution)
  - [Command Line Interface](#command-line-interface)
  - [Image Processing](#image-processing)
  - [Manual Control with Actor](#manual-control-with-actor)
- [Examples](#examples)
- [Socket.IO Server (Optional)](#socketio-server-optional)
  - [Installation](#installation-1)
  - [Running the Server](#running-the-server)
  - [Server Features](#server-features)
  - [Client Integration](#client-integration)
- [Documentation](#documentation)
- [License](#license)

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
export OAGI_API_KEY="your-api-key" # get your API key from https://developer.openagi.org/
# export OAGI_BASE_URL="https://api.agiopen.org/", # optional, defaults to production endpoint
```

### Automated Task Execution

Run tasks automatically with screenshot capture and action execution:

```python
import asyncio
from oagi import AsyncDefaultAgent, AsyncPyautoguiActionHandler, AsyncScreenshotMaker

async def main():
    agent = AsyncDefaultAgent(max_steps=10)
    completed = await agent.execute(
        "Search weather on Google",
        action_handler=AsyncPyautoguiActionHandler(),  # Executes mouse/keyboard actions
        image_provider=AsyncScreenshotMaker(),         # Captures screenshots
    )
    return completed

asyncio.run(main())
```

Configure PyAutoGUI behavior with custom settings:

```python
from oagi import AsyncPyautoguiActionHandler, PyautoguiConfig

# Customize action behavior
config = PyautoguiConfig(
    drag_duration=1.0,      # Slower drags for precision (default: 0.5)
    scroll_amount=50,       # Larger scroll steps (default: 30)
    wait_duration=2.0,      # Longer waits (default: 1.0)
    action_pause=0.2,       # More pause between actions (default: 0.1)
    hotkey_interval=0.1,    # Interval between keys in hotkey combinations (default: 0.1)
    capslock_mode="session" # Caps lock mode: 'session' or 'system' (default: 'session')
)

action_handler = AsyncPyautoguiActionHandler(config=config)
```

### Command Line Interface

Run agents directly from the terminal:

```bash
# Run with actor model
oagi agent run "Go to nasdaq.com, search for AAPL. Under More, go to Insider Activity" --model lux-actor-1

# Run with thinker mode (uses lux-thinker-1 model with more steps)
oagi agent run "Look up the store hours for the nearest Apple Store to zip code 23456 using the Apple Store Locator" --model lux-thinker-1

# Run pre-configured tasker workflows (no instruction needed)
oagi agent run --mode tasker:software_qa

# List all available modes
oagi agent modes

# Check macOS permissions (screen recording & accessibility)
oagi agent permission

# Export execution history
oagi agent run "Complete the form" --export html --export-file report.html
```

CLI options:
- `--mode`: Agent mode (default: actor). Use `oagi agent modes` to list available modes
- `--model`: Override the model (default: determined by mode)
- `--max-steps`: Maximum steps (default: determined by mode)
- `--temperature`: Sampling temperature (default: determined by mode)
- `--step-delay`: Delay after each action before next screenshot (default: 0.3s)
- `--export`: Export format (markdown, html, json)
- `--export-file`: Output file path for export

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

### Manual Control with Actor

For step-by-step control over task execution:

```python
import asyncio
from oagi import AsyncActor, AsyncPyautoguiActionHandler, AsyncScreenshotMaker

async def main():
    async with AsyncActor() as actor:
        await actor.init_task("Complete the form")
        image_provider = AsyncScreenshotMaker()
        action_handler = AsyncPyautoguiActionHandler()

        for _ in range(10):
            image = await image_provider()
            step = await actor.step(image)

            if step.stop:
                break

            await action_handler(step.actions)

asyncio.run(main())
```

## Examples

See the [`examples/`](examples/) directory for more usage patterns:
- `execute_task_auto.py` - Automated task execution with `AsyncDefaultAgent`
- `execute_task_manual.py` - Manual step-by-step control with `Actor`
- `continued_session.py` - Continuing tasks across sessions
- `screenshot_with_config.py` - Image compression and optimization
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

For full Lux documentation and guides, visit the [OAGI Developer Documentation](https://developer.agiopen.org/docs/index).

## License

MIT