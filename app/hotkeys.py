from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

from .window_manager import IS_WINDOWS, native_hotkey_id, register_slot_hotkeys, unregister_hotkeys


class HotkeyController(QAbstractNativeEventFilter):
    """Listener Ctrl+Alt+1..9 menggunakan RegisterHotKey Windows native."""

    def __init__(
        self,
        app: QCoreApplication,
        window_handle: int,
        callback: Callable[[int], None],
        slot_count: int = 9,
    ) -> None:
        super().__init__()
        self.app = app
        self.window_handle = int(window_handle)
        self.callback = callback
        self.slot_count = max(0, min(9, int(slot_count)))
        self.mapping: dict[int, int] = {}
        self._installed = False
        self._enabled = False

        if IS_WINDOWS:
            self.app.installNativeEventFilter(self)
            self._installed = True
            self.app.aboutToQuit.connect(self.close)
            self.set_enabled(True)

    @property
    def registered_count(self) -> int:
        return len(self.mapping)

    @property
    def enabled(self) -> bool:
        return bool(self._enabled and self.mapping)

    def set_enabled(self, enabled: bool) -> None:
        """Aktif/nonaktif hotkey tanpa melepas native event filter dari aplikasi."""
        if not IS_WINDOWS:
            self._enabled = False
            return

        enabled = bool(enabled)
        if enabled == self._enabled and (not enabled or self.mapping):
            return

        if self.mapping:
            unregister_hotkeys(self.window_handle, self.mapping.keys())
            self.mapping.clear()

        self._enabled = enabled
        if enabled:
            self.mapping = register_slot_hotkeys(
                self.window_handle,
                self.slot_count,
            )

    def nativeEventFilter(self, _event_type, message):
        if not self._enabled:
            return False, 0
        hotkey_id = native_hotkey_id(message)
        if hotkey_id is None:
            return False, 0
        slot = self.mapping.get(hotkey_id)
        if slot is None:
            return False, 0
        self.callback(slot)
        return True, 0

    def close(self) -> None:
        if IS_WINDOWS and self.mapping:
            unregister_hotkeys(self.window_handle, self.mapping.keys())
            self.mapping.clear()
        self._enabled = False
        if self._installed:
            try:
                self.app.removeNativeEventFilter(self)
            except Exception:
                pass
            self._installed = False
