import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.app_window import AppMainWindow
from app.auto_restore import StartupWorkspaceRestorer
from app.hotkeys import HotkeyController
from app.multi_monitor import MultiMonitorDragZoneController
from app.single_instance import SingleInstanceManager
from app.theme import STYLE
from app.tray import TrayController
from app.window_manager import IS_WINDOWS, WindowInfo, get_foreground_window


def run() -> int:
    start_hidden = "--tray" in sys.argv

    app = QApplication(sys.argv)
    app.setApplicationName("Bagi Layar")
    app.setOrganizationName("ToniTools")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))

    # Hanya satu engine boleh aktif. Launch manual kedua meminta instance lama
    # membuka UI; launch auto-start --tray kedua cukup keluar diam-diam.
    single_instance = SingleInstanceManager(app)
    if not single_instance.acquire_or_notify(show_existing=not start_hidden):
        return 0

    win = AppMainWindow()
    win.workspace_list.setObjectName("WorkspaceList")
    win.window_list.setObjectName("WindowList")
    win.lock_button.setObjectName("LockToggle")

    # Paksa refresh stylesheet setelah objectName khusus diterapkan.
    for widget in (win.workspace_list, win.window_list, win.lock_button):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    if not start_hidden:
        win.show()

    def move_foreground_to_slot(slot: int) -> None:
        targets = win._targets()
        if slot < 0 or slot >= len(targets):
            win.status_label.setText(
                f"Slot {slot + 1} tidak tersedia pada Monitor {win.selected_monitor + 1} "
                f"({win.layout_count} slot)"
            )
            return

        active = get_foreground_window(int(win.winId()))
        if active is None:
            win.status_label.setText("Tidak ada jendela aktif yang bisa dipindahkan")
            return

        if win._move_window_to_slot(active, slot):
            # Sinkronkan daftar jika jendela baru dibuka setelah Bagi Layar berjalan.
            win.refresh_windows()
            win._select_handle_in_list(active.handle)
            win.status_label.setText(
                f"Hotkey: {active.title[:28]} → Monitor {win.selected_monitor + 1}, Slot {slot + 1}"
            )

    # winId() sengaja dipanggil walau start_hidden agar RegisterHotKey mendapat HWND valid.
    hotkeys = HotkeyController(app, int(win.winId()), move_foreground_to_slot, 9)
    win.hotkey_controller = hotkeys

    def snap_dragged_window(active: WindowInfo, slot: int, monitor_index: int) -> None:
        screens = QApplication.screens()
        if not screens:
            return
        monitor_index = max(0, min(monitor_index, len(screens) - 1))
        win._select_monitor(monitor_index)
        if win._move_window_to_slot(active, slot):
            win.refresh_windows()
            win._select_handle_in_list(active.handle)
            win.status_label.setText(
                f"Zona: {active.title[:28]} → Monitor {monitor_index + 1}, Slot {slot + 1}"
            )

    zones = MultiMonitorDragZoneController(win, snap_dragged_window)
    win.zone_controller = zones
    app.aboutToQuit.connect(zones.close)

    tray = TrayController(app, win, hotkeys, zones)
    win.tray_controller = tray
    app.aboutToQuit.connect(tray.close)

    # Pulihkan workspace aktif secara bertahap ketika aplikasi/jendela lain
    # belum sempat terbuka saat login Windows.
    auto_restore = StartupWorkspaceRestorer(win)
    tray.bind_auto_restore(auto_restore)
    auto_restore.completed.connect(tray.notify_auto_restore_finished)
    win.auto_restore_controller = auto_restore
    app.aboutToQuit.connect(auto_restore.close)

    # Instance kedua yang dibuka manual membawa instance lama ke depan.
    single_instance.show_requested.connect(tray.show_window)
    if single_instance.consume_pending_show():
        tray.show_window()
    win.single_instance_manager = single_instance
    app.aboutToQuit.connect(single_instance.close)

    if start_hidden:
        if tray.available:
            win.hide()
        else:
            # Jangan biarkan aplikasi tidak terlihat jika system tray tidak tersedia.
            win.show()

    # Timer baru mulai setelah seluruh engine/tray siap.
    auto_restore.start_if_enabled()

    if IS_WINDOWS:
        zone_text = "Zona aktif" if tray.zone_action.isChecked() else "Zona nonaktif"
        if tray.hotkey_action.isChecked():
            hotkey_text = f"Hotkey {hotkeys.registered_count}/9"
        else:
            hotkey_text = "Hotkey nonaktif"
        tray_text = "Tray aktif" if tray.available else "Tray tidak tersedia"
        startup_text = "Auto-start aktif" if tray.startup_action.isChecked() else "Auto-start nonaktif"
        restore_text = (
            "Auto-restore aktif"
            if tray.auto_restore_action.isChecked()
            else "Auto-restore nonaktif"
        )
        win.status_label.setText(
            f"Multi-monitor • {zone_text} • {hotkey_text} • {tray_text} • "
            f"{startup_text} • {restore_text} • Single-instance"
        )

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
