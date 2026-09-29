from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QSettings, QTimer, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .startup import IS_WINDOWS as STARTUP_WINDOWS, is_startup_enabled, set_startup_enabled


class TrayController(QObject):
    """Menjaga Bagi Layar aktif di background melalui Windows system tray."""

    def __init__(self, app: QApplication, window, hotkeys, zones) -> None:
        super().__init__(window)
        self.app = app
        self.window = window
        self.hotkeys = hotkeys
        self.zones = zones
        self.settings = QSettings("ToniTools", "Bagi Layar")
        self._quitting = False
        self._notice_shown = False

        self.available = QSystemTrayIcon.isSystemTrayAvailable()
        self.tray = QSystemTrayIcon(self._make_icon(), self)
        self.tray.setToolTip("Bagi Layar • Window Manager")

        self.menu = QMenu()
        self.open_action = QAction("Buka Bagi Layar", self.menu)
        self.open_action.triggered.connect(self.show_window)
        self.menu.addAction(self.open_action)

        self.workspace_menu = self.menu.addMenu("Workspace Cepat")
        self.workspace_menu.aboutToShow.connect(self._rebuild_workspace_menu)
        self._rebuild_workspace_menu()
        self.menu.addSeparator()

        self.zone_action = QAction("Zona Drag", self.menu)
        self.zone_action.setCheckable(True)
        self.zone_action.setChecked(self.settings.value("zone_enabled", True, bool))
        self.zone_action.toggled.connect(self._set_zones_enabled)
        self.menu.addAction(self.zone_action)

        self.hotkey_action = QAction("Hotkey Ctrl+Alt+1…9", self.menu)
        self.hotkey_action.setCheckable(True)
        self.hotkey_action.setChecked(self.settings.value("hotkeys_enabled", True, bool))
        self.hotkey_action.toggled.connect(self._set_hotkeys_enabled)
        self.menu.addAction(self.hotkey_action)

        self.startup_action = QAction("Mulai bersama Windows", self.menu)
        self.startup_action.setCheckable(True)
        self.startup_action.setEnabled(STARTUP_WINDOWS)
        self.startup_action.setChecked(is_startup_enabled() if STARTUP_WINDOWS else False)
        self.startup_action.toggled.connect(self._set_startup_enabled)
        self.menu.addAction(self.startup_action)

        self.menu.addSeparator()
        self.quit_action = QAction("Keluar Bagi Layar", self.menu)
        self.quit_action.triggered.connect(self.quit_application)
        self.menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._tray_activated)
        self.window.installEventFilter(self)

        self._set_zones_enabled(self.zone_action.isChecked())
        self._set_hotkeys_enabled(self.hotkey_action.isChecked())

        if self.available:
            self.app.setQuitOnLastWindowClosed(False)
            self.tray.show()

    @staticmethod
    def _make_icon() -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#1677ff"))
        painter.drawRoundedRect(4, 4, 56, 56, 13, 13)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#ffffff"), 4))
        painter.drawRoundedRect(14, 15, 36, 32, 4, 4)
        painter.drawLine(26, 16, 26, 46)
        painter.drawLine(38, 16, 38, 46)
        painter.drawLine(15, 31, 49, 31)
        painter.end()
        return QIcon(pixmap)

    def _rebuild_workspace_menu(self) -> None:
        self.workspace_menu.clear()
        storage = getattr(self.window, "storage", None)
        if storage is None:
            action = self.workspace_menu.addAction("Workspace tidak tersedia")
            action.setEnabled(False)
            return

        names = storage.list_workspaces()
        active = str(getattr(self.window, "active_workspace", ""))
        if not names:
            action = self.workspace_menu.addAction("Belum ada workspace")
            action.setEnabled(False)
            return

        for name in names:
            data = storage.get_workspace(name)
            label = name if data else f"{name} (kosong)"
            action = QAction(label, self.workspace_menu)
            action.setCheckable(True)
            action.setChecked(name == active)
            action.setEnabled(bool(data))
            action.triggered.connect(
                lambda _checked=False, workspace_name=name: self._activate_workspace(workspace_name)
            )
            self.workspace_menu.addAction(action)

    def _activate_workspace(self, name: str) -> None:
        storage = getattr(self.window, "storage", None)
        if storage is None or not storage.get_workspace(name):
            return

        if name != getattr(self.window, "active_workspace", ""):
            workspace_list = getattr(self.window, "workspace_list", None)
            switched = False
            if workspace_list is not None:
                for index in range(workspace_list.count()):
                    item = workspace_list.item(index)
                    if str(item.data(Qt.ItemDataRole.UserRole) or "") == name:
                        self.window._workspace_clicked(item)
                        switched = True
                        break
            if not switched:
                self.window.active_workspace = name
                storage.set_active_workspace(name)
                self.window.saved = storage.get_workspace(name)
                if hasattr(self.window, "_restore_settings"):
                    self.window._restore_settings()

        self.window.restore_workspace()
        self._rebuild_workspace_menu()
        if hasattr(self.window, "status_label"):
            self.window.status_label.setText(f'Workspace "{name}" dipulihkan dari tray')
        if self.available:
            self.tray.showMessage(
                "Workspace dipulihkan",
                name,
                QSystemTrayIcon.MessageIcon.Information,
                1800,
            )

    def _set_zones_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        self.settings.setValue("zone_enabled", enabled)
        if self.zones is not None:
            self.zones.set_enabled(enabled)
        if hasattr(self.window, "status_label"):
            self.window.status_label.setText(
                "Zona drag aktif" if enabled else "Zona drag nonaktif"
            )

    def _set_hotkeys_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        self.settings.setValue("hotkeys_enabled", enabled)
        if self.hotkeys is not None:
            self.hotkeys.set_enabled(enabled)
        if hasattr(self.window, "status_label"):
            if enabled:
                count = getattr(self.hotkeys, "registered_count", 0)
                self.window.status_label.setText(f"Hotkey global aktif {count}/9")
            else:
                self.window.status_label.setText("Hotkey global nonaktif")

    def _set_startup_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if not STARTUP_WINDOWS:
            return
        if set_startup_enabled(enabled):
            if hasattr(self.window, "status_label"):
                self.window.status_label.setText(
                    "Mulai bersama Windows aktif" if enabled else "Mulai bersama Windows nonaktif"
                )
            return

        # Kembalikan check state jika registry per-user gagal diubah.
        self.startup_action.blockSignals(True)
        self.startup_action.setChecked(not enabled)
        self.startup_action.blockSignals(False)
        if hasattr(self.window, "status_label"):
            self.window.status_label.setText("Gagal mengubah pengaturan mulai bersama Windows")

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def hide_to_tray(self) -> None:
        if not self.available:
            return
        self.window.hide()
        if not self._notice_shown:
            self.tray.showMessage(
                "Bagi Layar tetap aktif",
                "Zona drag dan hotkey tetap berjalan dari system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
            self._notice_shown = True

    def _tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            if self.window.isVisible() and not self.window.isMinimized():
                self.window.hide()
            else:
                self.show_window()

    def eventFilter(self, watched, event):
        if watched is self.window and self.available and not self._quitting:
            if event.type() == QEvent.Type.Close:
                event.ignore()
                self.hide_to_tray()
                return True
            if event.type() == QEvent.Type.WindowStateChange and self.window.isMinimized():
                QTimer.singleShot(0, self.hide_to_tray)
        return super().eventFilter(watched, event)

    def quit_application(self) -> None:
        self._quitting = True
        self.window.removeEventFilter(self)
        self.tray.hide()
        self.window.close()
        self.app.quit()

    def close(self) -> None:
        self._quitting = True
        try:
            self.window.removeEventFilter(self)
        except Exception:
            pass
        self.tray.hide()
