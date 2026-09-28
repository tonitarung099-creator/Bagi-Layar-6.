from __future__ import annotations

from dataclasses import dataclass
import ctypes
import os
from ctypes import wintypes

from .layouts import Rect


@dataclass
class WindowInfo:
    handle: int
    title: str
    class_name: str = ""


IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

    SW_RESTORE = 9
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080


def list_windows(exclude_handle: int | None = None) -> list[WindowInfo]:
    if not IS_WINDOWS:
        return []

    windows: list[WindowInfo] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        if exclude_handle and int(hwnd) == int(exclude_handle):
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetParent(hwnd):
            return True
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex_style & WS_EX_TOOLWINDOW:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        title = title_buf.value.strip()
        if not title:
            return True
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        windows.append(WindowInfo(int(hwnd), title, class_buf.value))
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return windows


def move_window(handle: int, rect: Rect) -> bool:
    if not IS_WINDOWS:
        return False
    hwnd = wintypes.HWND(handle)
    try:
        user32.ShowWindow(hwnd, SW_RESTORE)
        return bool(
            user32.SetWindowPos(
                hwnd,
                0,
                int(rect.x),
                int(rect.y),
                int(rect.width),
                int(rect.height),
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
        )
    except Exception:
        return False
