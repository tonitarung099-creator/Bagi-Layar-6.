import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.hotkeys import HotkeyController
from app.main_window import MainWindow
from app.theme import STYLE
from app.window_manager import IS_WINDOWS, WindowInfo, get_foreground_window
from app.zone_overlay import WindowDragZoneController


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Bagi Layar")
    app.setOrganizationName("ToniTools")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))

    win = MainWindow()
    win.workspace_list.setObjectName("WorkspaceList")
    win.window_list.setObjectName("WindowList")
    win.lock_button.setObjectName("LockToggle")

    # Paksa refresh stylesheet setelah objectName khusus diterapkan.
    for widget in (win.workspace_list, win.window_list, win.lock_button):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    win.show()

    def move_foreground_to_slot(slot: int) -> None:
        targets = win._targets()
        if slot < 0 or slot >= len(targets):
            win.status_label.setText(
                f"Slot {slot + 1} tidak tersedia pada layout {win.layout_count} jendela"
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
                f"Hotkey: {active.title[:32]} → Slot {slot + 1}"
            )

    hotkeys = HotkeyController(app, int(win.winId()), move_foreground_to_slot, 9)
    # Simpan referensi agar native event filter tidak di-GC selama aplikasi hidup.
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
                f"Zona: {active.title[:30]} → Monitor {monitor_index + 1}, Slot {slot + 1}"
            )

    zones = WindowDragZoneController(win, snap_dragged_window)
    win.zone_controller = zones
    app.aboutToQuit.connect(zones.close)

    if IS_WINDOWS:
        if hotkeys.registered_count == 9:
            win.status_label.setText(
                "Zona drag aktif • Hotkey Ctrl+Alt+1 sampai Ctrl+Alt+9"
            )
        else:
            win.status_label.setText(
                f"Zona drag aktif • Hotkey {hotkeys.registered_count}/9 tersedia"
            )

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
