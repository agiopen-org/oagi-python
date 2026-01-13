# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------


import sys
from typing import List


class Screen:
    """
    Screen represents a single display screen.

    Attributes:
        name (str): The name of the screen.
        x (int): The x-coordinate of the top-left corner of the screen.
        y (int): The y-coordinate of the top-left corner of the screen.
        width (int): The width of the screen in pixels.
        height (int): The height of the screen in pixels.
        is_primary (bool): True if this is the primary screen, False otherwise.
    """

    def __init__(self, name, x, y, width, height, is_primary=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.name = name
        self.is_primary = is_primary

    def __str__(self):
        return f"Screen(name={self.name}, x={self.x}, y={self.y}, width={self.width}, height={self.height})"


class ScreenManager:
    """
    ScreenManager is responsible for detecting and managing screens.
    """

    def __init__(self):
        self.screens = {}
        # Enable DPI awareness if on Windows
        if sys.platform == "win32":
            self.enable_windows_dpi_awareness()

    def get_all_screens(self) -> dict[str, Screen]:
        if self.screens:
            return self.screens
        if sys.platform == "darwin":
            screens = self.get_darwin_screen_info()
        elif sys.platform == "win32":
            screens = self.get_windows_screen_info()
        else:
            screens = self.get_linux_screen_info()
        for screen in screens:
            if screen.is_primary:
                self.screens["primary"] = screen
            else:
                self.screens[screen.name] = screen
        return self.screens

    def get_darwin_screen_info(self) -> List[Screen]:
        """
        Get screen information for macOS using AppKit.

        Returns:
            List[Screen]: A list of Screen objects representing all detected screens.
        """
        import AppKit  # noqa: PLC0415

        # Force the RunLoop to update once
        # This "accepts input" which forces macOS to update screen geometry
        loop = AppKit.NSRunLoop.currentRunLoop()
        loop.acceptInputForMode_beforeDate_(
            AppKit.NSDefaultRunLoopMode, AppKit.NSDate.distantPast()
        )
        # Retrieve screen information using AppKit
        screens = AppKit.NSScreen.screens()
        screen_list = []
        for _, screen in enumerate(screens):
            frame = screen.frame()
            # Origin (0,0) is bottom-left of the primary screen
            x, y = int(frame.origin.x), int(frame.origin.y)
            width, height = int(frame.size.width), int(frame.size.height)
            name = screen.localizedName()
            # Normalize the origin to Top-Left
            y = int(AppKit.NSScreen.screens()[0].frame().size.height) - (y + height)
            screen_list.append(Screen(name, x, y, width, height, x == 0 and y == 0))
        return screen_list

    def get_windows_screen_info(self) -> List[Screen]:
        """
         Get screen information for windows using mss.

        Returns:
            List[Screen]: A list of Screen objects representing all detected screens.
        """
        import mss  # noqa: PLC0415

        screen_list = []
        for index, screen in enumerate(mss.mss().monitors[1:]):
            screen_list.append(
                Screen(
                    f"DISPLAY{index}",
                    screen["left"],
                    screen["top"],
                    screen["width"],
                    screen["height"],
                    screen["top"] == 0 and screen["left"] == 0,
                )
            )
        return screen_list

    def get_linux_screen_info(self) -> List[Screen]:
        """
        Get screen information for linux and other platform as default.

        Returns:
            List[Screen]: A list of Screen objects representing all detected screens.
        """
        import screeninfo  # noqa: PLC0415

        screen_list = []
        for screen in screeninfo.get_monitors():
            screen_list.append(
                Screen(
                    screen.name,
                    screen.x,
                    screen.y,
                    screen.width,
                    screen.height,
                    screen.is_primary,
                )
            )
        return screen_list

    def enable_windows_dpi_awareness(self):
        """
        Enable per-monitor DPI awareness to fix multi-monitor scaling issues.

        On Windows with mixed scaling between monitors, applications that are not
        DPI-aware will have their coordinates virtualized, causing clicks/moves to
        land at incorrect positions. Enabling DPI awareness ensures PyAutoGUI and mss
        works in physical pixels across all monitors.
        """
        import ctypes  # noqa: PLC0415

        try:
            # For Windows 8.1 and Windows 10/11
            # 2 = PROCESS_PER_MONITOR_DPI_AWARE
            PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
        except Exception:
            try:
                # Fallback for older Windows versions
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                raise RuntimeError("Could not set DPI awareness")
