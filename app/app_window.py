from __future__ import annotations

from PySide6.QtWidgets import QApplication

from .multi_monitor import MultiMonitorMainWindow


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
