from __future__ import annotations

import json
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem, QPushButton, QStyle

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.final_window import AppMainWindow
from app.fonts import preferred_ui_font
from app.sol_theme import STYLE


def visual_fixture(win: AppMainWindow) -> None:
    # Fixture screenshot saja; tidak dipakai produksi dan tidak memalsukan monitor nyata.
    win.workspace_list.clear()
    for name in ("ChatGPT 6 Runner", "Kerja Harian", "Desain & Riset"):
        item = QListWidgetItem(name)
        win.workspace_list.addItem(item)
    win.workspace_list.setCurrentRow(0)

    win.window_list.clear()
    for i in range(1, 7):
        item = QListWidgetItem(f"Chrome - Runner {i:02d}\nMonitor 1 • Slot {i}")
        item.setData(Qt.UserRole, 1000 + i)
        item.setIcon(win.style().standardIcon(QStyle.SP_FileIcon))
        win.window_list.addItem(item)

    while win.monitor_row.count():
        item = win.monitor_row.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    for i, res in enumerate(("1920 × 1080", "1920 × 1080", "2560 × 1440"), 1):
        b = QPushButton(f"Monitor {i}\n{'Utama • ' if i == 1 else ''}{res}", objectName="MonitorTab")
        b.setCheckable(True)
        b.setChecked(i == 1)
        b.setIcon(win.style().standardIcon(QStyle.SP_ComputerIcon))
        win.monitor_row.addWidget(b)
    add = QPushButton("Tambah / Monitor Lain", objectName="MonitorPlaceholder")
    win.monitor_row.addWidget(add)
    win.monitor_row.addStretch()

    win.preview.set_monitor_aspect(1920, 1080)
    win._select_layout(6)
    win.margin_spin.setValue(16)
    win.gap_spin.setValue(12)
    win.lock_button.setChecked(True)
    win.status_left.setText(
        "●  3 monitor   |   ● Monitor 1 1920×1080   ○ Monitor 2 1920×1080   ○ Monitor 3 2560×1440"
    )
    win.status_label.setText("Siap digunakan   ⓘ")


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setFont(preferred_ui_font(10))
    app.setStyleSheet(STYLE)
    out = ROOT / "artifacts" / "ui"
    out.mkdir(parents=True, exist_ok=True)

    win = AppMainWindow()
    win.lock_timer.stop()
    visual_fixture(win)
    results = []
    for width, height in ((1566, 914), (1366, 768), (1280, 720)):
        win.resize(width, height)
        win.show()
        for _ in range(8):
            app.processEvents()
        path = out / f"bagi-layar-{width}x{height}.png"
        ok = win.grab().save(str(path), "PNG")
        if not ok:
            raise RuntimeError(f"Gagal menyimpan screenshot {path}")
        results.append(
            {
                "size": [width, height],
                "actual": [win.width(), win.height()],
                "minimum": [win.minimumWidth(), win.minimumHeight()],
                "font": app.font().family(),
                "file": path.name,
            }
        )
    (out / "snapshot-metadata.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    win.close()
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())