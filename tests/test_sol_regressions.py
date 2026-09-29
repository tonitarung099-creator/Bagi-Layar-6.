from __future__ import annotations

import os
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem

from app.layouts import Rect
from app.sol_app_window import AppMainWindow
from app.window_manager import WindowInfo


APP = QApplication.instance() or QApplication([])


class FakeStorage:
    def __init__(self):
        self.active = "Tes"
        self.workspaces = {"Tes": {}}

    def active_workspace(self):
        return self.active

    def get_workspace(self, name):
        return deepcopy(self.workspaces.get(name, {}))

    def list_workspaces(self):
        return list(self.workspaces)

    def set_active_workspace(self, name):
        self.active = name

    def create_workspace(self, name):
        self.workspaces.setdefault(name, {})
        self.active = name

    def save_workspace(self, name, data):
        self.workspaces[name] = deepcopy(data)
        self.active = name


class SolRegressionTests(unittest.TestCase):
    def setUp(self):
        self.storage_patch = patch("app.main_window.Storage", FakeStorage)
        self.storage_patch.start()
        self.win = AppMainWindow()
        self.win.lock_timer.stop()

    def tearDown(self):
        self.win.close()
        self.storage_patch.stop()
        APP.processEvents()

    def _set_windows(self, windows):
        self.win.windows = list(windows)
        self.win.window_list.clear()
        for w in windows:
            item = QListWidgetItem(w.title)
            item.setData(Qt.UserRole, w.handle)
            self.win.window_list.addItem(item)

    def test_B01_lock_off_stays_off_after_arrange(self):
        windows = [WindowInfo(101, "A"), WindowInfo(102, "B")]
        self._set_windows(windows)
        for i in range(self.win.window_list.count()):
            self.win.window_list.item(i).setSelected(True)
        self.win.lock_button.setChecked(False)
        self.win._capture_current_profile()
        with patch("app.sol_app_window.move_window", return_value=True):
            self.win.arrange_windows()
        self.assertFalse(self.win.locked_rects)
        with patch("app.sol_app_window.window_exists", return_value=True), patch(
            "app.sol_app_window.enforce_window_rect"
        ) as enforce:
            self.win._enforce_lock()
        enforce.assert_not_called()

    def test_B02_handle_has_only_one_global_assignment(self):
        current = self.win._screen_key(self.win.selected_monitor)
        self.win.monitor_assignments = {
            "monitor-lama": {0: 101, 1: 102},
            current: {},
        }
        self.win._activate_assignment_map(self.win.selected_monitor)
        target = WindowInfo(101, "A")
        with patch("app.sol_app_window.move_window", return_value=True):
            self.assertTrue(self.win._move_window_to_slot(target, 0))
        owners = [
            (key, slot)
            for key, assignments in self.win.monitor_assignments.items()
            for slot, handle in assignments.items()
            if handle == 101
        ]
        self.assertEqual(len(owners), 1)
        self.assertEqual(self.win.monitor_assignments["monitor-lama"].get(1), 102)

    def test_B03_screen_identity_does_not_include_resolution(self):
        class FakeScreen:
            def __init__(self, serial):
                self._serial = serial
            def serialNumber(self): return self._serial
            def manufacturer(self): return "ACME"
            def model(self): return "Panel"
            def name(self): return "DISPLAY-X"
        base1, _ = self.win._screen_identity_parts(FakeScreen("SERIAL1"))
        base2, _ = self.win._screen_identity_parts(FakeScreen("SERIAL1"))
        self.assertEqual(base1, "serial:SERIAL1")
        self.assertEqual(base1, base2)
        self.assertNotIn("1920", base1)

    def test_B04_offline_monitor_never_enters_lock_cache(self):
        current = self.win._screen_key(self.win.selected_monitor)
        self.win.monitor_assignments = {current: {0: 101}, "offline-key": {0: 202}}
        self.win.monitor_profiles[current] = {**self.win._normalize_profile({}), "lock_layout": True}
        self.win.monitor_profiles["offline-key"] = {**self.win._normalize_profile({}), "lock_layout": True}
        with patch.object(
            self.win,
            "_connected_monitor_index_for_key",
            side_effect=lambda key: 0 if key == current else -1,
        ), patch.object(self.win, "_targets_for_monitor", return_value=[Rect(0, 0, 100, 100)]):
            self.win._rebuild_locked_rects()
        self.assertIn(101, self.win.locked_rects)
        self.assertNotIn(202, self.win.locked_rects)

    def test_B05_watcher_does_not_overwrite_active_profile(self):
        key = self.win._screen_key(self.win.selected_monitor)
        saved = {
            "monitors": {
                key: {
                    "layout_count": 2,
                    "margin": 1,
                    "gap": 1,
                    "lock_layout": True,
                    "slots": [],
                }
            }
        }
        self.win.storage.workspaces["Tes"] = deepcopy(saved)
        self.win.monitor_profiles[key] = self.win._normalize_profile(
            {"layout_count": 6, "margin": 16, "gap": 12, "lock_layout": True}
        )
        before = deepcopy(self.win.monitor_profiles[key])
        with patch("app.sol_app_window.list_windows", return_value=[]):
            self.win.restore_missing_workspace_windows()
        self.assertEqual(self.win.monitor_profiles[key], before)
        self.assertEqual(self.win.monitor_profiles[key]["layout_count"], 6)

    def test_B06_workspace_payload_preserves_offline_saved_slot(self):
        self.win.saved = {
            "workspace_schema": 3,
            "monitors": {
                "offline-key": {
                    "layout_count": 6,
                    "margin": 16,
                    "gap": 12,
                    "lock_layout": True,
                    "slots": [
                        {"slot": 3, "title": "Belum Dibuka", "class_name": "Chrome_WidgetWin_1"}
                    ],
                }
            },
        }
        self.win._load_saved_intent(self.win.saved)
        self.win.monitor_profiles["offline-key"] = self.win._normalize_profile(self.win.saved["monitors"]["offline-key"])
        self.win.windows = []
        payload = self.win._workspace_payload()
        self.assertEqual(payload["monitors"]["offline-key"]["slots"][0]["slot"], 3)
        self.assertEqual(payload["monitors"]["offline-key"]["slots"][0]["title"], "Belum Dibuka")

    def test_B07_double_click_signal_accepts_qt_signature(self):
        w = WindowInfo(101, "A")
        self._set_windows([w])
        item = self.win.window_list.item(0)
        with patch.object(self.win, "_move_window_to_slot", return_value=True) as move:
            self.win.window_list.itemDoubleClicked.emit(item)
            APP.processEvents()
        move.assert_called_once()

    def test_B08_cancel_add_workspace_is_transactional(self):
        key = self.win._screen_key(self.win.selected_monitor)
        self.win.layout_count = 9
        self.win.monitor_assignments[key] = {0: 101}
        self.win._activate_assignment_map(self.win.selected_monitor)
        before = (
            self.win.active_workspace,
            self.win.layout_count,
            deepcopy(self.win.monitor_assignments),
            deepcopy(self.win.monitor_profiles),
        )
        with patch("app.sol_app_window.QInputDialog.getText", return_value=("", False)):
            self.win._add_workspace()
        after = (
            self.win.active_workspace,
            self.win.layout_count,
            deepcopy(self.win.monitor_assignments),
            deepcopy(self.win.monitor_profiles),
        )
        self.assertEqual(after, before)

    def test_B09_cancel_custom_restores_layout_highlight(self):
        self.win._select_layout(6)
        self.win.layout_buttons[0].setChecked(True)  # state yang terjadi saat tombol Kustom diklik
        with patch("app.sol_app_window.QInputDialog.getInt", return_value=(2, False)):
            self.win._select_custom()
        self.assertEqual(self.win.layout_count, 6)
        self.assertTrue(self.win.layout_buttons[6].isChecked())
        self.assertFalse(self.win.layout_buttons[0].isChecked())

    def test_B10_sidebar_navigation_is_exclusive_and_actionable(self):
        self.win.nav_buttons[1].click()
        checked = [b.isChecked() for b in self.win.nav_buttons]
        self.assertEqual(checked, [False, True, False])
        self.assertTrue(self.win.window_list.hasFocus())
        self.win.nav_buttons[2].click()
        self.assertEqual([b.isChecked() for b in self.win.nav_buttons], [False, False, True])
        self.assertTrue(self.win.arrange_action.hasFocus())

    def test_B11_refresh_removes_only_truly_dead_hwnd(self):
        key = self.win._screen_key(self.win.selected_monitor)
        self.win.monitor_assignments[key] = {0: 101}
        self.win._activate_assignment_map(self.win.selected_monitor)
        with patch("app.main_window.list_windows", return_value=[]), patch(
            "app.sol_app_window.IS_WINDOWS", True
        ), patch("app.sol_app_window.window_exists", return_value=False):
            self.win.refresh_windows()
        self.assertNotIn(0, self.win.monitor_assignments[key])


if __name__ == "__main__":
    unittest.main()
