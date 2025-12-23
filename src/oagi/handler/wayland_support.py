# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import io
import logging
import os
import shlex
import shutil
import subprocess
import time

from screeninfo import get_monitors

from ..exceptions import check_optional_dependency
from ._ydotool import KEYCODE_MAP

check_optional_dependency("PIL", "PILImage", "desktop")
from PIL import Image  # noqa: E402

logger = logging.getLogger(__name__)


def is_wayland_display_server() -> bool:
    """Check if Wayland is the current display server."""
    return os.environ.get("WAYLAND_DISPLAY") is not None


def get_screen_size() -> tuple[int, int]:
    """Get the screen size in pixels."""
    for monitor in get_monitors():
        if monitor.is_primary:
            return monitor.width, monitor.height

    # Fallback if no monitor is marked primary
    monitors = get_monitors()
    if monitors:
        return monitors[0].width, monitors[0].height
    return None


def screenshot() -> Image:
    """
    Use Flameshot to take a screenshot and return an Image object

    :return: Image object of the screenshot
    """
    # Check if flameshot is installed
    if shutil.which("flameshot") is None:
        raise RuntimeError("flameshot not found. Ensure it is installed and in PATH.")
    cmd = ["flameshot", "full", "--region", "all", "--raw"]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(
            f"flameshot failed: {shlex.join(cmd)}, stdout: {res.stdout.decode(errors='ignore')}, stderr: {res.stderr.decode(errors='ignore')}"
        )
    im = Image.open(io.BytesIO(res.stdout))
    im.load()
    return im


class Ydotool:
    """
    Ydotool wrapper for Wayland display server.

    :param socket_address: The socket address for ydotool, default is empty string.
    """

    def __init__(self, socket_address: str = "") -> None:
        # Check if ydotool is installed
        if shutil.which("ydotool") is None:
            raise RuntimeError("ydotool not found. Ensure it is installed and in PATH.")
        # Set default delay between actions
        self.action_pause = 0.5
        # Last action time
        self.last_action_time = 0.0
        # Customize the socket address for ydotool
        self.socket_address = socket_address
        # Check environment issues for ydotool
        self.environ_check()

    def environ_check(self):
        """Check environment issues for ydotool"""
        # Check if ydotoold is running
        if not subprocess.run(
            ["pgrep", "ydotoold"], capture_output=True, text=True
        ).stdout.strip():
            logger.warning("Ydotool daemon (ydotoold) is not running")
        # Check the permission to access the socket address
        socket_address = (
            self.socket_address
            or os.environ.get("YDOOTOOL_SOCKET", "")
            or f"/run/user/{os.getuid()}/.ydotool_socket"
        )
        if not os.access(socket_address, os.W_OK) or not os.path.exists(socket_address):
            logger.warning(f"Ydotool cannot connect to socket address:{socket_address}")
        # Check if the mouse acceleration profile is 'flat' (For GNOME)
        accel_profile = subprocess.run(
            [
                "gsettings",
                "get",
                "org.gnome.desktop.peripherals.mouse",
                "accel-profile",
            ],
            capture_output=True,
            text=True,
        ).stdout.strip()
        if accel_profile and accel_profile != "'flat'":
            logger.warning(
                f"Mouse Acceleration is not disabled, current accel-profile is {accel_profile}). Ydotool may not work as expected.",
                "Please disable mouse acceleration by running 'gsettings set org.gnome.desktop.peripherals.mouse accel-profile 'flat''",
            )

    def _get_keycode(self, key_char: str) -> int:
        """
        Get the keycode from input-event-codes mapping.
        :param key_char: Key char (e.g., "A", "ENTER", "F1", "PRINT_SCREEN", case-insensitive)
        :return: Decimal keycode
        """
        # Lookup and return keycode
        if key_char in KEYCODE_MAP:
            return KEYCODE_MAP[key_char]
        else:
            return None

    def _run_ydotool(self, args: list[str], count: int = 1) -> None:
        """
        Run ydotool command; e.g., ["click", "500", "300"] => ydotool click 500 300
        """
        if interval := (time.time() - self.last_action_time) / 1000 < self.action_pause:
            time.sleep(interval)
        if count > 1:
            args.extend(["--repeat", str(count)])
        cmd = ["ydotool", *args]
        # Use shlex.join for clear logging
        logger.debug(f"[ydotool] {shlex.join(cmd)}")
        # Env with socket address
        env = os.environ.copy()
        if self.socket_address:
            env["YDOOTOOL_SOCKET"] = self.socket_address
        # Run ydotool command
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
        )
        if res.returncode != 0:
            raise RuntimeError(
                f"ydotool failed: {shlex.join(cmd)}, stdout: {res.stdout.decode(errors='ignore').strip()}, stderr: {res.stderr.decode(errors='ignore').strip()}"
            )
        self.last_action_time = time.time()

    def drag(self, x1: int, y1: int, x2: int, y2: int, count: int = 1) -> None:
        """
        Drag from (x1, y1) to (x2, y2).

        """
        for _ in range(count):
            self.mousemove(x1, y1)
            self._run_ydotool(["click", "0x40"])
            self.mousemove(x2, y2)
            self._run_ydotool(["click", "0x80"])

    def mousemove(self, x: int, y: int, count: int = 1) -> None:
        """
        Move mouse to (x, y).
        :param x: X coordinate of the mouse cursor
        :param y: Y coordinate of the mouse cursor
        :param count: Number of mouse move actions to perform
        """
        self._run_ydotool(
            ["mousemove", "--absolute", "-x", str(x), "-y", str(y)], count=count
        )

    def scroll(self, clicks: float) -> None:
        """
        Scroll mouse wheel in the given direction.
        :param clicks: Number of clicks to scroll, positive for up, negative for down
        """
        self._run_ydotool(
            [
                "mousemove",
                "-w",
                "--",
                "0",
                str(clicks),
            ],
        )

    def click(self, x: int, y: int, count: int = 1, right: bool = False) -> None:
        """
        Click at (x, y).
        """
        self.mousemove(x, y)
        if right:
            click_key = "0xC1"
        else:
            click_key = "0xC0"
        self._run_ydotool(["click", click_key], count=count)

    def type(self, text: str, count: int = 1) -> None:
        """
        Type the given text.
        """
        self._run_ydotool(["type", text], count=count)

    def hotkey(self, keys: list[str], count: int = 1) -> None:
        """
        Press and release the given keys.
        """
        hotkey_sequences = [
            self._get_keycode(key) for key in keys if self._get_keycode(key) is not None
        ]
        command_args = [f"{keycode}:1" for keycode in hotkey_sequences] + [
            f"{keycode}:0" for keycode in hotkey_sequences[::-1]
        ]
        self._run_ydotool(["key", *command_args], count=count)
