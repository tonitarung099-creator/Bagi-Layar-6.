from dataclasses import dataclass
import unittest

from app.window_matcher import find_best_window, normalize_title, window_match_score


@dataclass
class FakeWindow:
    handle: int
    title: str
    class_name: str = "Chrome_WidgetWin_1"
    process_name: str = "chrome.exe"


class WindowMatcherTests(unittest.TestCase):
    def test_normalize_browser_suffix(self):
        self.assertEqual(normalize_title("Runner 01 - Google Chrome"), "runner 01")

    def test_exact_identity_wins(self):
        saved = {
            "title": "ChatGPT Runner 02 - Google Chrome",
            "class_name": "Chrome_WidgetWin_1",
            "process_name": "chrome.exe",
        }
        windows = [
            FakeWindow(1, "ChatGPT Runner 01 - Google Chrome"),
            FakeWindow(2, "ChatGPT Runner 02 - Google Chrome"),
        ]
        self.assertEqual(find_best_window(saved, windows).handle, 2)

    def test_title_can_change_but_runner_identity_still_matches(self):
        saved = {
            "title": "ChatGPT - Runner 03 - Google Chrome",
            "class_name": "Chrome_WidgetWin_1",
            "process_name": "chrome.exe",
        }
        windows = [
            FakeWindow(3, "Runner 03 | ChatGPT Queue - Google Chrome"),
            FakeWindow(4, "Runner 04 | ChatGPT Queue - Google Chrome"),
        ]
        self.assertEqual(find_best_window(saved, windows).handle, 3)

    def test_wrong_process_is_rejected(self):
        saved = {
            "title": "Dokumen Proyek",
            "class_name": "Chrome_WidgetWin_1",
            "process_name": "chrome.exe",
        }
        edge = FakeWindow(9, "Dokumen Proyek", process_name="msedge.exe")
        self.assertEqual(window_match_score(saved, edge), 0.0)

    def test_used_window_is_not_reused(self):
        saved = {
            "title": "Runner 01",
            "class_name": "Chrome_WidgetWin_1",
            "process_name": "chrome.exe",
        }
        windows = [FakeWindow(1, "Runner 01"), FakeWindow(2, "Runner 02")]
        self.assertIsNone(find_best_window(saved, windows, {1}))

    def test_unique_process_class_fallback_when_title_changes_totally(self):
        saved = {
            "title": "Laporan Lama",
            "class_name": "Notepad",
            "process_name": "notepad.exe",
        }
        windows = [
            FakeWindow(11, "Untitled", class_name="Notepad", process_name="notepad.exe"),
            FakeWindow(12, "Runner", class_name="Chrome_WidgetWin_1", process_name="chrome.exe"),
        ]
        self.assertEqual(find_best_window(saved, windows).handle, 11)


if __name__ == "__main__":
    unittest.main()
