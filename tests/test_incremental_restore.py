import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from app.app_window import AppMainWindow
from app.window_manager import WindowInfo


class _Storage:
    def __init__(self, data):
        self.data = data

    def get_workspace(self, _name):
        return self.data


class IncrementalRestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_only_missing_slot_is_moved(self):
        win = AppMainWindow()
        win.active_workspace = "Test"
        key = win._screen_key(0)
        existing = WindowInfo(101, "Runner 01 - Google Chrome", "Chrome_WidgetWin_1", "chrome.exe")
        replacement = WindowInfo(202, "Runner 02 - ChatGPT - Google Chrome", "Chrome_WidgetWin_1", "chrome.exe")
        win.monitor_assignments = {key: {0: existing.handle}}
        win._activate_assignment_map(0)
        win.storage = _Storage(
            {
                "workspace_schema": 3,
                "active_monitor_key": key,
                "monitors": {
                    key: {
                        "monitor_index": 0,
                        "layout_count": 2,
                        "margin": 0,
                        "gap": 0,
                        "taskbar_mode": 0,
                        "lock_layout": True,
                        "slots": [
                            {
                                "slot": 0,
                                "title": "Runner 01 - Google Chrome",
                                "class_name": "Chrome_WidgetWin_1",
                                "process_name": "chrome.exe",
                            },
                            {
                                "slot": 1,
                                "title": "Runner 02 - Google Chrome",
                                "class_name": "Chrome_WidgetWin_1",
                                "process_name": "chrome.exe",
                            },
                        ],
                    }
                },
            }
        )

        moved_handles = []

        def _move(handle, _rect):
            moved_handles.append(handle)
            return True

        with patch("app.app_window.list_windows", return_value=[existing, replacement]), patch(
            "app.app_window.window_exists", side_effect=lambda handle: handle == existing.handle
        ), patch("app.app_window.move_window", side_effect=_move):
            moved, missing, offline = win.restore_missing_workspace_windows()

        self.assertEqual((moved, missing, offline), (1, 0, 0))
        self.assertEqual(moved_handles, [replacement.handle])
        self.assertEqual(win.monitor_assignments[key][0], existing.handle)
        self.assertEqual(win.monitor_assignments[key][1], replacement.handle)
        win.close()


if __name__ == "__main__":
    unittest.main()
