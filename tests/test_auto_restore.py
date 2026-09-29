import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.auto_restore import StartupWorkspaceRestorer


class _Storage:
    def __init__(self, data):
        self.data = data

    def get_workspace(self, _name):
        return self.data


class _Label:
    def setText(self, _text):
        pass


class _Window:
    def __init__(self, data):
        self.storage = _Storage(data)
        self.active_workspace = "Tes"
        self.monitor_assignments = {"screen-0": {0: 101}}
        self.status_label = _Label()
        self.restore_calls = 0

    def _screen_key(self, _index):
        return "screen-0"

    def restore_workspace(self):
        self.restore_calls += 1


class AutoRestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_expected_slots_ignores_offline_monitor(self):
        data = {
            "monitors": {
                "screen-0": {"slots": [{"slot": 0}, {"slot": 1}]},
                "monitor-offline": {"slots": [{"slot": 0}]},
            }
        }
        window = _Window(data)
        controller = StartupWorkspaceRestorer(window)
        self.assertEqual(controller.expected_slots(), 2)
        controller.close()

    def test_legacy_slots_are_counted(self):
        window = _Window({"slots": [{"slot": 0}, {"slot": 1}, {"slot": 2}]})
        controller = StartupWorkspaceRestorer(window)
        self.assertEqual(controller.expected_slots(), 3)
        controller.close()

    def test_current_slots_counts_all_monitor_assignments(self):
        window = _Window({"slots": []})
        window.monitor_assignments = {
            "screen-0": {0: 101, 1: 102},
            "screen-1": {0: 201},
        }
        controller = StartupWorkspaceRestorer(window)
        self.assertEqual(controller.current_slots(), 3)
        controller.close()


if __name__ == "__main__":
    unittest.main()
