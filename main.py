import sys

from PySide6.QtWidgets import QApplication

from app.sol_app_window import AppMainWindow, MultiMonitorDragZoneController
from app.auto_restore import StartupWorkspaceRestorer
from app.fonts import preferred_ui_font
from app.hotkeys import HotkeyController
from app.single_instance import SingleInstanceManager
from app.sol_theme import STYLE
from app.tray import TrayController
from app.window_manager import IS_WINDOWS, WindowInfo, get_foreground_window
from app.workspace_watch import WorkspaceWatchController


def run() -> int:
    start_hidden = "--tray" in sys.argv

    app = QApplication(sys.argv)
    app.setApplicationName("Bagi Layar")
    app.setOrganizationName("ToniTools")
    app.setStyle("Fusion")
    app.setFont(preferred_ui_font(10))
    app.setStyleSheet(STYLE)

    single_instance = SingleInstanceManager(app)
    if not single_instance.acquire_or_notify(show_existing=not start_hidden):
        return 0

    win = AppMainWindow()

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
            win.refresh_windows()
            win._select_handle_in_list(active.handle)
            win.status_label.setText(
                f"Hotkey: {active.title[:28]} → Monitor {win.selected_monitor + 1}, Slot {slot + 1}"
            )

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

    auto_restore = StartupWorkspaceRestorer(win)
    tray.bind_auto_restore(auto_restore)
    auto_restore.completed.connect(tray.notify_auto_restore_finished)
    win.auto_restore_controller = auto_restore
    app.aboutToQuit.connect(auto_restore.close)

    workspace_watch = WorkspaceWatchController(win)
    tray.bind_workspace_watch(workspace_watch)
    workspace_watch.recovered.connect(tray.notify_workspace_recovered)
    win.workspace_watch_controller = workspace_watch
    app.aboutToQuit.connect(workspace_watch.close)

    single_instance.show_requested.connect(tray.show_window)
    if single_instance.consume_pending_show():
        tray.show_window()
    win.single_instance_manager = single_instance
    app.aboutToQuit.connect(single_instance.close)

    if start_hidden:
        if tray.available:
            win.hide()
        else:
            win.show()

    auto_restore.start_if_enabled()
    workspace_watch.start_if_enabled()

    if IS_WINDOWS:
        zone_text = "Zona aktif" if tray.zone_action.isChecked() else "Zona nonaktif"
        hotkey_text = (
            f"Hotkey {hotkeys.registered_count}/9"
            if tray.hotkey_action.isChecked()
            else "Hotkey nonaktif"
        )
        tray_text = "Tray aktif" if tray.available else "Tray tidak tersedia"
        startup_text = "Auto-start aktif" if tray.startup_action.isChecked() else "Auto-start nonaktif"
        restore_text = "Auto-restore aktif" if tray.auto_restore_action.isChecked() else "Auto-restore nonaktif"
        watch_text = "Pantau workspace aktif" if tray.workspace_watch_action.isChecked() else "Pantau workspace nonaktif"
        win.status_label.setText("Siap digunakan   ⓘ")
        win.status_label.setToolTip(
            " • ".join(
                [
                    "Multi-monitor",
                    zone_text,
                    hotkey_text,
                    tray_text,
                    startup_text,
                    restore_text,
                    watch_text,
                    "Single-instance",
                ]
            )
        )

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())