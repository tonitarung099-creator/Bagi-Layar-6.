from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox

from .multi_monitor import MultiMonitorMainWindow
from .window_manager import move_window


class AppMainWindow(MultiMonitorMainWindow):
    """Lapisan hardening untuk perilaku aplikasi produksi."""

    def _monitor_index_for_key(self, key: str, fallback: int = 0) -> int:
        """Cari monitor aktif; fallback negatif berarti monitor memang offline."""
        screens = QApplication.screens()
        for index in range(len(screens)):
            if self._screen_key(index) == key:
                return index

        try:
            fallback_index = int(fallback)
        except Exception:
            fallback_index = 0

        # Dipakai oleh Kunci Layout untuk membedakan monitor tersambung vs offline.
        # Jangan pernah memaksa monitor offline menjadi Monitor 1.
        if fallback_index < 0:
            return -1
        if not screens:
            return 0
        return max(0, min(fallback_index, len(screens) - 1))

    def _connected_monitor_index_for_key(self, key: str) -> int:
        """Return -1 jika identitas monitor tersimpan sedang tidak tersambung."""
        for index in range(len(QApplication.screens())):
            if self._screen_key(index) == str(key):
                return index
        return -1

    def restore_workspace(self):
        """Restore workspace tanpa memindahkan slot monitor offline ke monitor lain."""
        data = self.storage.get_workspace(self.active_workspace)
        if not data:
            QMessageBox.information(
                self,
                "Workspace",
                "Workspace ini belum memiliki susunan tersimpan.",
            )
            return

        self.saved = data
        self._restore_settings()
        self.refresh_windows()
        self.monitor_assignments = {
            self._screen_key(index): {} for index in range(len(QApplication.screens()))
        }
        by_exact = {(w.title, w.class_name): w for w in self.windows}
        by_title = {w.title: w for w in self.windows}
        used_handles: set[int] = set()
        moved = 0
        offline_monitors = 0

        monitors = data.get("monitors")
        if isinstance(monitors, dict):
            items = list(monitors.items())
            legacy = False
        else:
            # Workspace lama tidak mempunyai identitas monitor permanen.
            key = self._screen_key(self.selected_monitor)
            items = [(key, {**self._legacy_profile(data), "slots": data.get("slots", [])})]
            legacy = True

        for saved_key, entry in items:
            if not isinstance(entry, dict):
                continue

            if legacy:
                monitor_index = self.selected_monitor
            else:
                monitor_index = self._connected_monitor_index_for_key(str(saved_key))
                if monitor_index < 0:
                    offline_monitors += 1
                    continue

            current_key = self._screen_key(monitor_index)
            self.monitor_profiles[current_key] = self._normalize_profile(entry)
            assignments = self.monitor_assignments.setdefault(current_key, {})
            targets = self._targets_for_monitor(monitor_index)

            slots = entry.get("slots", [])
            if not isinstance(slots, list):
                continue
            for saved_slot in slots:
                if not isinstance(saved_slot, dict):
                    continue
                try:
                    slot = int(saved_slot.get("slot", -1))
                except Exception:
                    continue
                if not (0 <= slot < len(targets)):
                    continue

                title = str(saved_slot.get("title", ""))
                class_name = str(saved_slot.get("class_name", ""))
                win = by_exact.get((title, class_name)) or by_title.get(title)
                if not win or win.handle in used_handles:
                    continue
                if move_window(win.handle, targets[slot]):
                    assignments[slot] = win.handle
                    used_handles.add(win.handle)
                    moved += 1

        self._activate_assignment_map(self.selected_monitor)
        self._apply_monitor_profile(self.selected_monitor)
        self._rebuild_locked_rects()
        self._update_monitor_button_labels()
        self._update_preview_assignments()
        self._update_window_list_labels()

        suffix = f" • {offline_monitors} monitor offline dilewati" if offline_monitors else ""
        self.status_label.setText(
            f"Workspace multi-monitor dipulihkan • {moved} jendela diposisikan{suffix}"
        )
