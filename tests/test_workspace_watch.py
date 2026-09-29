import unittest
from types import SimpleNamespace

from PySide6.QtCore import QCoreApplication, QObject

from app.workspace_watch import WorkspaceWatchController


class _Window(QObject):
    def __init__(self, result=(1, 2, 0)):
        super().__init__()
        self.result = result
        self.calls = 0
        self.auto_restore_controller = SimpleNamespace(running=False)

    def restore_missing_workspace_windows(self):
        self.calls += 1
        return self.result


class WorkspaceWatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_poll_recovers_missing_windows(self):
        window = _Window((1, 2, 0))
        controller = WorkspaceWatchController(window, interval_ms=2000)
        controller.running = True
        emitted = []
        controller.recovered.connect(lambda moved, missing, offline: emitted.append((moved, missing, offline)))

        result = controller.poll_once()

        self.assertEqual(result, (1, 2, 0))
        self.assertEqual(window.calls, 1)
        self.assertEqual(emitted, [(1, 2, 0)])
        controller.set_enabled(False)
        controller.close()

    def test_poll_waits_while_startup_restore_is_running(self):
        window = _Window((1, 0, 0))
        window.auto_restore_controller = SimpleNamespace(running=True)
        controller = WorkspaceWatchController(window)
        controller.running = True

        result = controller.poll_once()

        self.assertEqual(result, (0, 0, 0))
        self.assertEqual(window.calls, 0)
        controller.set_enabled(False)
        controller.close()

    def test_interval_has_safe_minimum(self):
        window = _Window((0, 0, 0))
        controller = WorkspaceWatchController(window, interval_ms=100)
        self.assertGreaterEqual(controller.interval_ms, 1500)
        controller.set_enabled(False)
        controller.close()


if __name__ == "__main__":
    unittest.main()
