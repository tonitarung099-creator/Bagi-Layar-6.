from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, QTimer, Signal

from .paths import config_file


class WorkspaceWatchController(QObject):
    """Pantau slot workspace kosong dan pulihkan jendela yang muncul belakangan."""

    recovered = Signal(int, int, int)

    def __init__(self, window, *, interval_ms: int = 4000, parent=None) -> None:
        qt_parent = parent if isinstance(parent, QObject) else window if isinstance(window, QObject) else None
        super().__init__(qt_parent)
        self.window = window
        self.interval_ms = max(1500, int(interval_ms))
        self.settings = QSettings(
            str(config_file("settings.ini")),
            QSettings.Format.IniFormat,
            self,
        )
        self.timer = QTimer(self)
        self.timer.setInterval(self.interval_ms)
        self.timer.timeout.connect(self.poll_once)
        self.running = False

    def is_enabled(self) -> bool:
        return self.settings.value("watch_workspace", False, bool)

    def set_enabled(self, enabled: bool) -> None:
        self.settings.setValue("watch_workspace", bool(enabled))
        self.settings.sync()

    def start_if_enabled(self) -> None:
        if self.is_enabled():
            self.start()

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.timer.start()
        QTimer.singleShot(900, self.poll_once)

    def stop(self) -> None:
        self.running = False
        self.timer.stop()

    def poll_once(self) -> tuple[int, int, int]:
        if not self.running:
            return 0, 0, 0

        # Saat startup auto-restore sedang melakukan retry penuh, watcher tidak ikut
        # bergerak agar desktop tidak disentuh dua controller pada waktu yang sama.
        auto_restore = getattr(self.window, "auto_restore_controller", None)
        if auto_restore is not None and bool(getattr(auto_restore, "running", False)):
            return 0, 0, 0

        restore_missing = getattr(self.window, "restore_missing_workspace_windows", None)
        if not callable(restore_missing):
            return 0, 0, 0

        try:
            moved, missing, offline = restore_missing()
            result = int(moved), int(missing), int(offline)
        except Exception:
            return 0, 0, 0

        if result[0] > 0:
            self.recovered.emit(*result)
        return result

    def close(self) -> None:
        self.stop()
        self.settings.sync()
