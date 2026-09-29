from __future__ import annotations

from dataclasses import dataclass
import ctypes
import os
from ctypes import wintypes

from .layouts import Rect


IS_WINDOWS = os.name == "nt"


@dataclass(frozen=True)
class NativeMonitor:
    device: str
    monitor: Rect
    work: Rect
    primary: bool = False


def _rect_from_win32(value) -> Rect:
    return Rect(
        int(value.left),
        int(value.top),
        max(1, int(value.right - value.left)),
        max(1, int(value.bottom - value.top)),
    )


def enumerate_native_monitors() -> list[NativeMonitor]:
    """Enumerasi monitor dalam koordinat native Windows.

    Engine penempatan memakai koordinat ini agar QScreen device-independent pixels
    tidak diteruskan mentah ke SetWindowPos pada konfigurasi mixed-DPI.
    """
    if not IS_WINDOWS:
        return []

    user32 = ctypes.windll.user32
    MONITORINFOF_PRIMARY = 0x00000001

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
            ("szDevice", wintypes.WCHAR * 32),
        ]

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )

    try:
        user32.EnumDisplayMonitors.argtypes = [
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            MonitorEnumProc,
            wintypes.LPARAM,
        ]
        user32.EnumDisplayMonitors.restype = wintypes.BOOL
        user32.GetMonitorInfoW.argtypes = [
            wintypes.HMONITOR,
            ctypes.POINTER(MONITORINFOEXW),
        ]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
    except Exception:
        pass

    result: list[NativeMonitor] = []

    def callback(hmonitor, _hdc, _rect, _lparam):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        try:
            if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                result.append(
                    NativeMonitor(
                        device=str(info.szDevice or "").strip(),
                        monitor=_rect_from_win32(info.rcMonitor),
                        work=_rect_from_win32(info.rcWork),
                        primary=bool(info.dwFlags & MONITORINFOF_PRIMARY),
                    )
                )
        except Exception:
            pass
        return True

    callback_ref = MonitorEnumProc(callback)
    try:
        user32.EnumDisplayMonitors(0, None, callback_ref, 0)
    except Exception:
        return []
    return result


def native_monitor_for_qscreen(screen) -> NativeMonitor | None:
    """Cocokkan QScreen ke monitor Win32 tanpa bergantung pada resolusi.

    QScreen.name() pada Windows biasanya sama dengan MONITORINFOEX.szDevice.
    Jika driver tidak menyediakan nama yang cocok, fallback hanya dipakai bila
    ada tepat satu monitor sehingga tidak berisiko menebak monitor yang salah.
    """
    monitors = enumerate_native_monitors()
    if not monitors:
        return None
    try:
        name = str(screen.name() or "").strip().casefold()
    except Exception:
        name = ""
    if name:
        matches = [m for m in monitors if m.device.casefold() == name]
        if len(matches) == 1:
            return matches[0]
    if len(monitors) == 1:
        return monitors[0]
    return None


def qt_rect_from_native(screen, native: Rect) -> Rect:
    """Konversi rect native ke ruang Qt milik monitor yang sama.

    Konversi dilakukan per-monitor dengan pemetaan affine origin+size; tidak
    mengalikan seluruh virtual desktop dengan satu DPR global.
    """
    mapping = native_monitor_for_qscreen(screen)
    if mapping is None:
        return native
    q = screen.geometry()
    src = mapping.monitor
    sx = q.width() / max(1, src.width)
    sy = q.height() / max(1, src.height)
    return Rect(
        int(round(q.x() + (native.x - src.x) * sx)),
        int(round(q.y() + (native.y - src.y) * sy)),
        max(1, int(round(native.width * sx))),
        max(1, int(round(native.height * sy))),
    )


def native_point_monitor_index(screens, x: int, y: int) -> int:
    """Temukan index QScreen dari point native tanpa QGuiApplication.screenAt()."""
    for index, screen in enumerate(screens):
        mapping = native_monitor_for_qscreen(screen)
        if mapping is None:
            continue
        r = mapping.monitor
        if r.x <= x < r.x + r.width and r.y <= y < r.y + r.height:
            return index
    return -1
