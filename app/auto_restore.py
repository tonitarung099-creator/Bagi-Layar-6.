from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, QTimer, Signal
from PySide6.QtGui import QGuiApplication

from .paths import config_file


class StartupWorkspaceRestorer(QObject):
    """Pulihkan workspace aktif saat mulai dan ketika monitor kembali tersambung."""

    progress = Signal(int, int, int)
    completed = Signal(bool, int, int)

    def __init__(
        self,
        window,
        *,
        retry_interval_ms: int = 5000,
        max_attempts: int = 18,
        initial_delay_ms: int = 3000,
        parent=None,
    ) -> None:
        qt_parent = parent if isinstance(parent, QObject) else None
        if qt_parent is None and isinstance(window, QObject):
            qt_parent = window
        super().__init__(qt_parent)
        self.window = window
        self.retry_interval_ms = max(1000, int(retry_interval_ms))
        self.max_attempts = max(1, int(max_attempts))
        self.initial_delay_ms = max(0, int(initial_delay_ms))
        self.settings = QSettings(
            str(config_file("settings.ini")),
            QSettings.Format.IniFormat,
            self,
        )
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._attempt_restore)
        self.attempt = 0
        self.running = False
        self._gui_app = QGuiApplication.instance()
        if self._gui_app is not None:
            try:
                self._gui_app.screenAdded.connect(self._screen_added)
            except Exception:
                pass

    def is_enabled(self) -> bool:
        return self.settings.value("auto_restore_workspace", False, bool)

    def set_enabled(self, enabled: bool) -> None:
        self.settings.setValue("auto_restore_workspace", bool(enabled))
        self.settings.sync()

    def start_if_enabled(self) -> None:
        if self.is_enabled():
            self.start(self.initial_delay_ms)

    def start(self, delay_ms: int | None = None) -> None:
        expected = self.expected_slots()
        if expected <= 0:
            self.stop()
            return
        self.stop()
        self.running = True
        self.attempt = 0
        self.timer.start(self.initial_delay_ms if delay_ms is None else max(0, int(delay_ms)))

    def stop(self) -> None:
        self.timer.stop()
        self.running = False
        self.attempt = 0

    def _screen_added(self, _screen) -> None:
        # QScreen sudah terdaftar di QApplication ketika sinyal ini diterima.
        # Beri jeda sedikit agar geometry/profile monitor stabil lebih dulu.
        if self.is_enabled():
            self.start(1500)

    def expected_slots(self) -> int:
        storage = getattr(self.window, "storage", None)
        workspace = str(getattr(self.window, "active_workspace", ""))
        if storage is None or not workspace:
            return 0
        data = storage.get_workspace(workspace)
        if not isinstance(data, dict):
            return 0

        monitors = data.get("monitors")
        if isinstance(monitors, dict):
            connected_keys = set()
            try:
                from PySide6.QtWidgets import QApplication

                connected_keys = {
                    self.window._screen_key(index)
                    for index in range(len(QApplication.screens()))
                }
            except Exception:
                pass

            total = 0
            for key, entry in monitors.items():
                if connected_keys and str(key) not in connected_keys:
                    continue
                if isinstance(entry, dict):
                    slots = entry.get("slots", [])
                    if isinstance(slots, list):
                        total += len(slots)
            return total

        slots = data.get("slots", [])
        return len(slots) if isinstance(slots, list) else 0

    def current_slots(self) -> int:
        assignments = getattr(self.window, "monitor_assignments", None)
        if isinstance(assignments, dict):
            return sum(len(value) for value in assignments.values() if isinstance(value, dict))
        slots = getattr(self.window, "slot_assignments", None)
        return len(slots) if isinstance(slots, dict) else 0

    def _attempt_restore(self) -> None:
        if not self.running:
            return

        self.attempt += 1
        expected = self.expected_slots()
        if expected <= 0:
            self.stop()
            return

        try:
            self.window.restore_workspace()
        except Exception:
            # Jangan mematikan engine hanya karena satu percobaan restore gagal.
            pass

        current = min(self.current_slots(), expected)
        self.progress.emit(current, expected, self.attempt)
        if hasattr(self.window, "status_label"):
            self.window.status_label.setText(
                f"Auto-restore workspace • {current}/{expected} jendela • "
                f"percobaan {self.attempt}/{self.max_attempts}"
            )

        if current >= expected:
            self.running = False
            self.timer.stop()
            self.completed.emit(True, current, expected)
            return

        if self.attempt >= self.max_attempts:
            self.running = False
            self.timer.stop()
            self.completed.emit(False, current, expected)
            return

        self.timer.start(self.retry_interval_ms)

    def close(self) -> None:
        self.stop()
        if self._gui_app is not None:
            try:
                self._gui_app.screenAdded.disconnect(self._screen_added)
            except Exception:
                pass
        self.settings.sync()
