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
        self.mapping: dict[int, int] = {}
        self._installed = False

        if IS_WINDOWS:
            self.mapping = register_slot_hotkeys(self.window_handle, slot_count)
            self.app.installNativeEventFilter(self)
            self._installed = True
            self.app.aboutToQuit.connect(self.close)

    @property
    def registered_count(self) -> int:
        return len(self.mapping)

    def nativeEventFilter(self, _event_type, message):
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
        if self._installed:
            try:
                self.app.removeNativeEventFilter(self)
            except Exception:
                pass
            self._installed = False
