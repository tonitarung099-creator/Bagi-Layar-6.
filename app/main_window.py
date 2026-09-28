from __future__ import annotations

import sys
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .layouts import Rect, build_grid
from .storage import Storage
from .widgets import ActionCard, LayoutButton, MonitorPreview
from .window_manager import IS_WINDOWS, WindowInfo, list_windows, move_window


STYLE = r"""
QMainWindow, QWidget { background: #f5f8fc; color: #121722; font-family: "Segoe UI"; font-size: 13px; }
#TopBar { background: #fbfdff; border-bottom: 1px solid #e3e9f1; }
#AppTitle { font-size: 21px; font-weight: 700; }
#AppSub { color: #6d7686; font-size: 11px; }
#Sidebar { background: #eef4fb; border-right: 1px solid #dce5f0; }
#NavButton { text-align: left; border: 0; border-radius: 10px; padding: 10px 12px; font-weight: 600; background: transparent; }
#NavButton:hover { background: #e1ecfb; }
#NavButton:checked { color: #0c5fd7; background: #dceaff; border-left: 4px solid #1677ff; }
#SectionTitle { font-weight: 700; font-size: 14px; }
#Subtle { color: #798395; font-size: 11px; }
#Card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }
#MonitorTab { background: #ffffff; border: 1px solid #dfe6ef; border-radius: 10px; padding: 10px 16px; text-align: left; min-width: 150px; }
#MonitorTab:checked { color: #075fd5; background: #eaf3ff; border: 1px solid #2985ff; }
QListWidget { background: transparent; border: 0; outline: 0; }
QListWidget::item { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 9px; padding: 8px 9px; margin: 2px 0; }
QListWidget::item:selected { color: #084fb5; background: #dceaff; border: 1px solid #91bfff; }
QPushButton#LayoutPreset { background: #ffffff; border: 1px solid #dfe6ef; padding: 8px; color: #303744; }
QPushButton#LayoutPreset:hover { border-color: #95bdf1; background: #f8fbff; }
QPushButton#LayoutPreset:checked { border: 2px solid #2681ff; background: #eaf3ff; color: #075fd5; font-weight: 700; }
QComboBox, QSpinBox { background: #ffffff; border: 1px solid #d6dee8; border-radius: 8px; padding: 7px 10px; min-height: 20px; }
QSlider::groove:horizontal { height: 5px; background: #d8dee8; border-radius: 2px; }
QSlider::handle:horizontal { width: 16px; margin: -6px 0; border-radius: 8px; background: #1779ee; }
QSlider::sub-page:horizontal { background: #1779ee; border-radius: 2px; }
#ActionCard { background: #ffffff; border: 1px solid #dfe6ef; border-radius: 10px; }
#ActionCard:hover { border-color: #9dc4f5; background: #fbfdff; }
#ActionPrimary { background: #1478f5; border: 1px solid #1478f5; border-radius: 10px; }
#ActionPrimary QLabel { color: white; }
#ActionTitle { font-weight: 700; }
#ActionSubtitle { color: #788293; font-size: 10px; }
#ActionPrimary #ActionSubtitle { color: #dcecff; }
#ActionIcon { font-size: 22px; }
QToolButton { border: 0; border-radius: 7px; padding: 6px; background: transparent; }
QToolButton:hover { background: #e9f1fb; }
QStatusBar { background: #fbfdff; border-top: 1px solid #e2e8f0; color: #596374; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bagi Layar")
        self.resize(1600, 920)
        self.setMinimumSize(1220, 720)
        self.storage = Storage()
        self.saved = self.storage.load()
        self.layout_count = int(self.saved.get("layout_count", 6))
        saved_shape = self.saved.get("custom_shape", [])
        self.custom_shape = tuple(saved_shape) if saved_shape else None
        self.windows: list[WindowInfo] = []
        self.monitor_buttons: list[QPushButton] = []
        self.selected_monitor = min(int(self.saved.get("monitor_index", 0)), max(0, len(QApplication.screens()) - 1))

        self._build_ui()
        self._refresh_monitors()
        self.refresh_windows()
        self._restore_settings()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top = QFrame(objectName="TopBar")
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(18, 12, 18, 12)
        logo = QLabel("▣")
        logo.setStyleSheet("background:#1976f3;color:white;border-radius:8px;padding:7px;font-size:18px;font-weight:700;")
        top_l.addWidget(logo)
        titles = QVBoxLayout()
        titles.addWidget(QLabel("Bagi Layar", objectName="AppTitle"))
        titles.addWidget(QLabel("Atur jendela, maksimalkan produktivitas.", objectName="AppSub"))
        top_l.addLayout(titles)
        top_l.addStretch()
        settings = QToolButton()
        settings.setText("⚙")
        settings.setToolTip("Pengaturan")
        top_l.addWidget(settings)
        outer.addWidget(top)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)
        body.addWidget(self._build_sidebar())

        content = QWidget()
        content_l = QVBoxLayout(content)
        content_l.setContentsMargins(16, 14, 16, 10)
        content_l.setSpacing(10)
        main_row = QHBoxLayout()
        main_row.setSpacing(10)
        main_row.addWidget(self._build_center(), 1)
        main_row.addWidget(self._build_settings())
        content_l.addLayout(main_row, 1)
        content_l.addWidget(self._build_actions())
        body.addWidget(content, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_label = QLabel("Siap digunakan")
        status.addPermanentWidget(self.status_label)

    def _build_sidebar(self) -> QWidget:
        side = QFrame(objectName="Sidebar")
        side.setFixedWidth(285)
        l = QVBoxLayout(side)
        l.setContentsMargins(14, 14, 14, 12)
        l.setSpacing(7)
        for index, (text, icon, sub) in enumerate([
            ("Workspace", "▦", "Kelola layout dan monitor"),
            ("Daftar Jendela", "▣", "Lihat dan atur jendela aktif"),
            ("Aksi Cepat", "ϟ", "Eksekusi tindakan dengan cepat"),
        ]):
            btn = QPushButton(f"{icon}   {text}\n      {sub}", objectName="NavButton")
            btn.setCheckable(True)
            btn.setChecked(index == 0)
            btn.setMinimumHeight(54)
            l.addWidget(btn)

        l.addSpacing(8)
        workspace_row = QHBoxLayout()
        workspace_row.addWidget(QLabel("Workspace", objectName="SectionTitle"))
        workspace_row.addStretch()
        add = QToolButton()
        add.setText("+")
        add.clicked.connect(self._add_workspace)
        workspace_row.addWidget(add)
        l.addLayout(workspace_row)

        self.workspace_list = QListWidget()
        self.workspace_list.setMaximumHeight(138)
        for name in ["ChatGPT 6 Runner", "Kerja Harian", "Desain & Riset"]:
            self.workspace_list.addItem(f"▣   {name}")
        self.workspace_list.setCurrentRow(0)
        l.addWidget(self.workspace_list)

        win_row = QHBoxLayout()
        win_row.addWidget(QLabel("Daftar Jendela", objectName="SectionTitle"))
        win_row.addStretch()
        refresh = QToolButton()
        refresh.setText("↻")
        refresh.clicked.connect(self.refresh_windows)
        win_row.addWidget(refresh)
        l.addLayout(win_row)

        self.window_list = QListWidget()
        self.window_list.setSelectionMode(QListWidget.SingleSelection)
        l.addWidget(self.window_list, 1)
        return side

    def _build_center(self) -> QWidget:
        panel = QFrame(objectName="Card")
        l = QVBoxLayout(panel)
        l.setContentsMargins(18, 14, 18, 14)
        l.setSpacing(10)
        l.addWidget(QLabel("Monitor Aktif", objectName="SectionTitle"))
        self.monitor_row = QHBoxLayout()
        self.monitor_group = QButtonGroup(self)
        self.monitor_group.setExclusive(True)
        l.addLayout(self.monitor_row)
        self.preview = MonitorPreview()
        l.addWidget(self.preview, 1)
        l.addWidget(QLabel("Pilih Layout", objectName="SectionTitle"))

        preset_row = QHBoxLayout()
        preset_row.setSpacing(7)
        self.layout_group = QButtonGroup(self)
        self.layout_group.setExclusive(True)
        self.layout_buttons: dict[int, LayoutButton] = {}
        for count, label in [(2, "2 Jendela"), (3, "3 Jendela"), (4, "4 Jendela"), (6, "6 Jendela"), (8, "8 Jendela"), (9, "9 Jendela")]:
            btn = LayoutButton(count, label)
            btn.setObjectName("LayoutPreset")
            btn.selected.connect(self._select_layout)
            self.layout_group.addButton(btn)
            self.layout_buttons[count] = btn
            preset_row.addWidget(btn)
        custom = LayoutButton(0, "Kustom")
        custom.setObjectName("LayoutPreset")
        custom.selected.connect(self._select_custom)
        self.layout_group.addButton(custom)
        self.layout_buttons[0] = custom
        preset_row.addWidget(custom)
        l.addLayout(preset_row)
        return panel

    def _build_settings(self) -> QWidget:
        panel = QFrame(objectName="Card")
        panel.setFixedWidth(335)
        l = QVBoxLayout(panel)
        l.setContentsMargins(18, 16, 18, 16)
        l.setSpacing(12)
        l.addWidget(QLabel("Pengaturan Monitor", objectName="SectionTitle"))

        l.addWidget(QLabel("Resolusi"))
        self.resolution = QComboBox()
        self.resolution.setEnabled(False)
        l.addWidget(self.resolution)

        l.addWidget(QLabel("Margin luar"))
        row = QHBoxLayout()
        self.margin_slider = QSlider(Qt.Horizontal)
        self.margin_slider.setRange(0, 60)
        self.margin_slider.setValue(16)
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 60)
        self.margin_spin.setSuffix(" px")
        self.margin_slider.valueChanged.connect(self.margin_spin.setValue)
        self.margin_spin.valueChanged.connect(self.margin_slider.setValue)
        row.addWidget(self.margin_slider, 1)
        row.addWidget(self.margin_spin)
        l.addLayout(row)

        l.addWidget(QLabel("Jarak antar jendela"))
        row2 = QHBoxLayout()
        self.gap_slider = QSlider(Qt.Horizontal)
        self.gap_slider.setRange(0, 50)
        self.gap_slider.setValue(12)
        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(0, 50)
        self.gap_spin.setSuffix(" px")
        self.gap_slider.valueChanged.connect(self.gap_spin.setValue)
        self.gap_spin.valueChanged.connect(self.gap_slider.setValue)
        row2.addWidget(self.gap_slider, 1)
        row2.addWidget(self.gap_spin)
        l.addLayout(row2)

        l.addWidget(QLabel("Area taskbar"))
        self.taskbar_mode = QComboBox()
        self.taskbar_mode.addItems(["Otomatis (Deteksi)", "Gunakan seluruh layar"])
        l.addWidget(self.taskbar_mode)
        l.addWidget(QLabel("Secara otomatis menyesuaikan area taskbar\nberdasarkan posisi dan ukuran.", objectName="Subtle"))

        l.addSpacing(8)
        lock_row = QHBoxLayout()
        lock_row.addWidget(QLabel("🔒  Kunci layout"))
        lock_row.addStretch()
        self.lock_button = QPushButton("Aktif")
        self.lock_button.setCheckable(True)
        self.lock_button.setChecked(True)
        self.lock_button.setFixedWidth(70)
        lock_row.addWidget(self.lock_button)
        l.addLayout(lock_row)
        l.addWidget(QLabel("Menjaga susunan tersimpan agar mudah\ndipulihkan kembali.", objectName="Subtle"))
        l.addStretch()
        return panel

    def _build_actions(self) -> QWidget:
        panel = QFrame(objectName="Card")
        l = QVBoxLayout(panel)
        l.setContentsMargins(16, 10, 16, 12)
        l.setSpacing(8)
        l.addWidget(QLabel("Aksi Cepat", objectName="SectionTitle"))
        row = QHBoxLayout()
        row.setSpacing(10)
        arrange = ActionCard("Susun Jendela", "Terapkan layout ke jendela aktif", "▦", True)
        restore = ActionCard("Pulihkan Layout", "Kembalikan ke layout tersimpan", "↻")
        save = ActionCard("Simpan Workspace", "Simpan layout saat ini", "▣")
        move = ActionCard("Pindahkan ke Slot", "Pilih jendela dan slot tujuan", "→")
        arrange.clicked.connect(self.arrange_windows)
        restore.clicked.connect(self.restore_workspace)
        save.clicked.connect(self.save_workspace)
        move.clicked.connect(self.move_selected_to_slot)
        for widget in (arrange, restore, save, move):
            row.addWidget(widget, 1)
        l.addLayout(row)
        return panel

    def _refresh_monitors(self):
        while self.monitor_row.count():
            item = self.monitor_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.monitor_buttons.clear()
        screens = QApplication.screens()
        for i, screen in enumerate(screens):
            geo = screen.geometry()
            suffix = "Utama " if screen == QApplication.primaryScreen() else ""
            btn = QPushButton(f"▣  Monitor {i+1}\n    {suffix}({geo.width()} × {geo.height()})", objectName="MonitorTab")
            btn.setCheckable(True)
            btn.setChecked(i == self.selected_monitor)
            btn.clicked.connect(partial(self._select_monitor, i))
            self.monitor_group.addButton(btn)
            self.monitor_row.addWidget(btn)
            self.monitor_buttons.append(btn)
        placeholder = QPushButton("＋  Tambah / Monitor lain", objectName="MonitorTab")
        placeholder.setToolTip("Monitor baru akan muncul otomatis ketika terdeteksi Windows.")
        placeholder.clicked.connect(lambda: QMessageBox.information(self, "Monitor", "Hubungkan monitor tambahan ke Windows. Bagi Layar akan mendeteksinya otomatis."))
        self.monitor_row.addWidget(placeholder)
        self._update_resolution()

    def _select_monitor(self, index: int):
        self.selected_monitor = index
        self._update_resolution()

    def _update_resolution(self):
        screens = QApplication.screens()
        if not screens:
            return
        self.selected_monitor = min(self.selected_monitor, len(screens)-1)
        g = screens[self.selected_monitor].geometry()
        self.resolution.clear()
        self.resolution.addItem(f"{g.width()} × {g.height()}")

    def _select_layout(self, count: int):
        self.layout_count = count
        self.custom_shape = None
        self.preview.set_layout_count(count)
        for c, button in self.layout_buttons.items():
            button.setChecked(c == count)

    def _select_custom(self, _ignored=0):
        rows, ok = QInputDialog.getInt(self, "Layout Kustom", "Jumlah baris:", 2, 1, 6)
        if not ok:
            return
        cols, ok = QInputDialog.getInt(self, "Layout Kustom", "Jumlah kolom:", 3, 1, 8)
        if not ok:
            return
        self.custom_shape = (rows, cols)
        self.layout_count = rows * cols
        self.preview.set_layout_count(self.layout_count, self.custom_shape)
        self.layout_buttons[0].setChecked(True)

    def refresh_windows(self):
        app_handle = int(self.winId()) if IS_WINDOWS else None
        self.windows = list_windows(app_handle)
        self.window_list.clear()
        for i, win in enumerate(self.windows):
            item = QListWidgetItem(f"▣   {win.title}\n      Belum ditetapkan")
            item.setData(Qt.UserRole, i)
            self.window_list.addItem(item)
        if self.windows:
            self.window_list.setCurrentRow(0)
        self.status_label.setText(f"{len(QApplication.screens())} monitor terdeteksi • {len(self.windows)} jendela aktif")

    def _screen_rect(self) -> Rect:
        screen = QApplication.screens()[self.selected_monitor]
        qrect = screen.availableGeometry() if self.taskbar_mode.currentIndex() == 0 else screen.geometry()
        return Rect(qrect.x(), qrect.y(), qrect.width(), qrect.height())

    def _targets(self):
        return build_grid(
            self._screen_rect(),
            self.layout_count,
            margin=self.margin_spin.value(),
            gap=self.gap_spin.value(),
            custom_shape=self.custom_shape,
        )

    def arrange_windows(self):
        self.refresh_windows()
        targets = self._targets()
        chosen = self.windows[:len(targets)]
        if not chosen:
            QMessageBox.warning(self, "Tidak ada jendela", "Tidak ada jendela aplikasi lain yang terdeteksi.")
            return
        moved = 0
        for win, rect in zip(chosen, targets):
            moved += int(move_window(win.handle, rect))
        self.status_label.setText(f"{moved} jendela disusun pada Monitor {self.selected_monitor + 1}")
        if not IS_WINDOWS:
            QMessageBox.information(self, "Mode pratinjau", "Pengaturan jendela sebenarnya hanya aktif di Windows.")

    def move_selected_to_slot(self):
        item = self.window_list.currentItem()
        if item is None or not self.windows:
            QMessageBox.warning(self, "Pilih jendela", "Pilih satu jendela pada Daftar Jendela terlebih dahulu.")
            return
        idx = item.data(Qt.UserRole)
        targets = self._targets()
        slot, ok = QInputDialog.getInt(self, "Pindahkan ke Slot", f"Nomor slot (1-{len(targets)}):", 1, 1, len(targets))
        if ok and move_window(self.windows[idx].handle, targets[slot - 1]):
            self.status_label.setText(f"Jendela dipindahkan ke Slot {slot}")

    def save_workspace(self):
        data = {
            "workspace": self.workspace_list.currentItem().text() if self.workspace_list.currentItem() else "ChatGPT 6 Runner",
            "monitor_index": self.selected_monitor,
            "layout_count": self.layout_count,
            "custom_shape": list(self.custom_shape) if self.custom_shape else [],
            "margin": self.margin_spin.value(),
            "gap": self.gap_spin.value(),
            "taskbar_mode": self.taskbar_mode.currentIndex(),
            "window_titles": [w.title for w in self.windows[:self.layout_count]],
        }
        self.storage.save(data)
        self.saved = data
        self.status_label.setText("Workspace berhasil disimpan")

    def restore_workspace(self):
        data = self.storage.load()
        if not data:
            QMessageBox.information(self, "Workspace", "Belum ada workspace yang disimpan.")
            return
        self.saved = data
        self._restore_settings()
        self.refresh_windows()
        by_title = {w.title: w for w in self.windows}
        targets = self._targets()
        moved = 0
        for title, rect in zip(data.get("window_titles", []), targets):
            win = by_title.get(title)
            if win:
                moved += int(move_window(win.handle, rect))
        self.status_label.setText(f"Workspace dipulihkan • {moved} jendela diposisikan")

    def _restore_settings(self):
        self.margin_spin.setValue(int(self.saved.get("margin", 16)))
        self.gap_spin.setValue(int(self.saved.get("gap", 12)))
        self.taskbar_mode.setCurrentIndex(int(self.saved.get("taskbar_mode", 0)))
        if self.custom_shape:
            self.preview.set_layout_count(self.layout_count, self.custom_shape)
            self.layout_buttons[0].setChecked(True)
        else:
            self._select_layout(self.layout_count if self.layout_count in self.layout_buttons else 6)

    def _add_workspace(self):
        name, ok = QInputDialog.getText(self, "Workspace Baru", "Nama workspace:")
        if ok and name.strip():
            self.workspace_list.addItem(f"▣   {name.strip()}")
            self.workspace_list.setCurrentRow(self.workspace_list.count() - 1)


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Bagi Layar")
    app.setOrganizationName("ToniTools")
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    return app.exec()
