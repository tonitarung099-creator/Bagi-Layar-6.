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
    process_name: str = ""


IS_WINDOWS = os.name == "nt"
WM_HOTKEY = 0x0312
HOTKEY_BASE_ID = 0xB600
VK_LBUTTON = 0x01
DWMWA_CLOAKED = 14

if IS_WINDOWS:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    try:
        dwmapi = ctypes.windll.dwmapi
    except Exception:
        dwmapi = None
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
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_NOREPEAT = 0x4000
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    # ctypes memakai c_int sebagai return type default. HANDLE Windows 64-bit harus
    # dideklarasikan eksplisit agar OpenProcess tidak terpotong di build x64.
    try:
        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
    except Exception:
        pass


def _is_cloaked(hwnd) -> bool:
    """True untuk surface Windows/UWP tersembunyi yang bukan jendela nyata pengguna."""
    if not IS_WINDOWS or dwmapi is None:
        return False
    try:
        cloaked = wintypes.DWORD(0)
        result = dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_CLOAKED,
            ctypes.byref(cloaked),
            ctypes.sizeof(cloaked),
        )
        return result == 0 and bool(cloaked.value)
    except Exception:
        return False


def _process_name_for_window(hwnd) -> str:
    """Nama executable pemilik HWND, contoh chrome.exe. Aman jika akses ditolak."""
    if not IS_WINDOWS:
        return ""
    pid = wintypes.DWORD(0)
    process = None
    try:
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not process:
            return ""
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
            return ""
        path = buffer.value.strip().replace("\\", "/")
        return path.rsplit("/", 1)[-1] if path else ""
    except Exception:
        return ""
    finally:
        if process:
            try:
                kernel32.CloseHandle(process)
            except Exception:
                pass


def _window_info(handle: int, exclude_handle: int | None = None) -> WindowInfo | None:
    if not IS_WINDOWS:
        return None
    hwnd = wintypes.HWND(handle)
    try:
        if exclude_handle and handle == int(exclude_handle):
            return None
        if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
            return None
        if user32.GetParent(hwnd):
            return None
        if _is_cloaked(hwnd):
            return None
        try:
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if ex_style & WS_EX_TOOLWINDOW:
                return None
        except Exception:
            pass

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return None
        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        title = title_buf.value.strip()
        if not title:
            return None

        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        return WindowInfo(
            handle,
            title,
            class_buf.value,
            _process_name_for_window(hwnd),
        )
    except Exception:
        return None


def list_windows(exclude_handle: int | None = None) -> list[WindowInfo]:
    if not IS_WINDOWS:
        return []

    windows: list[WindowInfo] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        info = _window_info(int(hwnd), exclude_handle)
        if info is not None:
            windows.append(info)
        return True

    callback_ref = EnumWindowsProc(callback)
    user32.EnumWindows(callback_ref, 0)
    return windows


def get_foreground_window(exclude_handle: int | None = None) -> WindowInfo | None:
    """Ambil jendela foreground saat ini tanpa mengubah fokus."""
    if not IS_WINDOWS:
        return None
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        return _window_info(int(hwnd), exclude_handle)
    except Exception:
        return None


def get_cursor_position() -> tuple[int, int] | None:
    """Posisi pointer global Windows dalam koordinat virtual desktop."""
    if not IS_WINDOWS:
        return None
    point = wintypes.POINT()
    try:
        if not user32.GetCursorPos(ctypes.byref(point)):
            return None
        return int(point.x), int(point.y)
    except Exception:
        return None


def is_left_button_down() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
    except Exception:
        return False


def get_window_rect(handle: int) -> Rect | None:
    if not IS_WINDOWS:
        return None
    rect = wintypes.RECT()
    try:
        if not user32.IsWindow(wintypes.HWND(handle)):
            return None
        if not user32.GetWindowRect(wintypes.HWND(handle), ctypes.byref(rect)):
            return None
        return Rect(
            int(rect.left),
            int(rect.top),
            max(1, int(rect.right - rect.left)),
            max(1, int(rect.bottom - rect.top)),
        )
    except Exception:
        return None


def move_window(handle: int, rect: Rect) -> bool:
    if not IS_WINDOWS:
        return False
    hwnd = wintypes.HWND(handle)
    try:
        if not user32.IsWindow(hwnd):
            return False
        # SetWindowPos tidak selalu mengubah ukuran jendela yang masih berstatus
        # minimized/maximized. Kembalikan ke state normal terlebih dahulu.
        if user32.IsIconic(hwnd) or user32.IsZoomed(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        return bool(
            user32.SetWindowPos(
                hwnd,
                0,
                int(rect.x),
                int(rect.y),
                max(1, int(rect.width)),
                max(1, int(rect.height)),
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
        )
    except Exception:
        return False


def window_exists(handle: int) -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(user32.IsWindow(wintypes.HWND(handle)))
    except Exception:
        return False


def register_slot_hotkeys(window_handle: int, slot_count: int = 9) -> dict[int, int]:
    """Daftarkan Ctrl+Alt+1..9. Return mapping hotkey_id -> slot index."""
    if not IS_WINDOWS:
        return {}

    mapping: dict[int, int] = {}
    hwnd = wintypes.HWND(window_handle)
    modifiers = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    for slot in range(max(0, min(9, slot_count))):
        hotkey_id = HOTKEY_BASE_ID + slot
        virtual_key = ord("1") + slot
        try:
            if user32.RegisterHotKey(hwnd, hotkey_id, modifiers, virtual_key):
                mapping[hotkey_id] = slot
        except Exception:
            continue
    return mapping


def unregister_hotkeys(window_handle: int, hotkey_ids) -> None:
    if not IS_WINDOWS:
        return
    hwnd = wintypes.HWND(window_handle)
    for hotkey_id in list(hotkey_ids):
        try:
            user32.UnregisterHotKey(hwnd, int(hotkey_id))
        except Exception:
            pass


def native_hotkey_id(message) -> int | None:
    """Ekstrak hotkey id dari native Windows MSG milik Qt."""
    if not IS_WINDOWS:
        return None
    try:
        msg = wintypes.MSG.from_address(int(message))
        if int(msg.message) == WM_HOTKEY:
            return int(msg.wParam)
    except Exception:
        return None
    return None
