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
        handle = int(hwnd)
        if exclude_handle and handle == int(exclude_handle):
            return True
        if not user32.IsWindowVisible(hwnd) or user32.GetParent(hwnd):
            return True
        try:
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if ex_style & WS_EX_TOOLWINDOW:
                return True
        except Exception:
            pass
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
        windows.append(WindowInfo(handle, title, class_buf.value))
        return True

    callback_ref = EnumWindowsProc(callback)
    user32.EnumWindows(callback_ref, 0)
    return windows


def move_window(handle: int, rect: Rect) -> bool:
    if not IS_WINDOWS:
        return False
    hwnd = wintypes.HWND(handle)
    try:
        if not user32.IsWindow(hwnd):
            return False
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        return bool(user32.SetWindowPos(hwnd, 0, int(rect.x), int(rect.y), max(1, int(rect.width)), max(1, int(rect.height)), SWP_NOZORDER | SWP_NOACTIVATE))
    except Exception:
        return False


def window_exists(handle: int) -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(user32.IsWindow(wintypes.HWND(handle)))
    except Exception:
        return False
