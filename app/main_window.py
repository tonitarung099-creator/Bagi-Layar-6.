from __future__ import annotations

import sys
from functools import partial

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
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
from .widgets import ActionCard, LayoutButton, MonitorPreview, WindowListWidget
from .window_manager import IS_WINDOWS, WindowInfo, list_windows, move_window, window_exists


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bagi Layar")
        self.resize(1600, 920)
        self.setMinimumSize(1220, 720)

        self.storage = Storage()
        self.active_workspace = self.storage.active_workspace()
        self.saved = self.storage.get_workspace(self.active_workspace)
        self.layout_count = int(self.saved.get("layout_count", 6))
        saved_shape = self.saved.get("custom_shape", [])
        self.custom_shape = tuple(saved_shape) if isinstance(saved_shape, list) and len(saved_shape) == 2 else None

        self.windows: list[WindowInfo] = []
        self.monitor_buttons: list[QPushButton] = []
        self.selected_monitor = 0
        self.slot_assignments: dict[int, int] = {}
        self.locked_rects: dict[int, Rect] = {}

        self._build_ui()
        self._refresh_monitors()
        self.refresh_windows()
        self._restore_settings()
        self._refresh_workspace_list()

        app = QApplication.instance()
        if app:
            app.screenAdded.connect(self._refresh_monitors)
            app.screenRemoved.connect(self._refresh_monitors)

        self.lock_timer = QTimer(self)
        self.lock_timer.timeout.connect(self._enforce_lock)
        self.lock_timer.start(1500)

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
        logo.setStyleSheet(
            "background:#1976f3;color:white;border-radius:8px;padding:7px;"
            "font-size:18px;font-weight:700;"
        )
        top_l.addWidget(logo)
        titles = QVBoxLayout()
        titles.addWidget(QLabel("Bagi Layar", objectName="AppTitle"))
        titles.addWidget(QLabel("Atur jendela, maksimalkan produktivitas.", objectName="AppSub"))
        top_l.addLayout(titles)
        top_l.addStretch()
        settings = QToolButton()
        settings.setText("⚙")
        settings.setToolTip("Pengaturan")
        settings.clicked.connect(
            lambda: QMessageBox.information(
                self,
                "Pengaturan",
                "Pengaturan monitor dan layout tersedia di panel kanan.",
            )
        )
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
        self.status_left = QLabel("Memeriksa monitor…")
        self.status_label = QLabel("Siap digunakan")
        status.addWidget(self.status_left)
        status.addPermanentWidget(self.status_label)

    def _build_sidebar(self) -> QWidget:
        side = QFrame(objectName="Sidebar")
        side.setFixedWidth(285)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(7)

        nav_items = [
            ("Workspace", "▦", "Kelola layout dan monitor"),
            ("Daftar Jendela", "▣", "Lihat dan atur jendela aktif"),
            ("Aksi Cepat", "ϟ", "Eksekusi tindakan dengan cepat"),
        ]
        for index, (text, icon, sub) in enumerate(nav_items):
            btn = QPushButton(f"{icon}   {text}\n      {sub}", objectName="NavButton")
            btn.setCheckable(True)
            btn.setChecked(index == 0)
            btn.setMinimumHeight(54)
            layout.addWidget(btn)

        layout.addSpacing(8)
        workspace_row = QHBoxLayout()
        workspace_row.addWidget(QLabel("Workspace", objectName="SectionTitle"))
        workspace_row.addStretch()
        add = QToolButton()
        add.setText("+")
        add.setToolTip("Tambah workspace")
        add.clicked.connect(self._add_workspace)
        workspace_row.addWidget(add)
        layout.addLayout(workspace_row)

        self.workspace_list = QListWidget()
        self.workspace_list.setMaximumHeight(150)
        self.workspace_list.itemClicked.connect(self._workspace_clicked)
        layout.addWidget(self.workspace_list)

        win_row = QHBoxLayout()
        win_row.addWidget(QLabel("Daftar Jendela", objectName="SectionTitle"))
        win_row.addStretch()
        refresh = QToolButton()
        refresh.setText("↻")
        refresh.setToolTip("Muat ulang jendela aktif")
        refresh.clicked.connect(self.refresh_windows)
        win_row.addWidget(refresh)
        layout.addLayout(win_row)

        hint = QLabel("Tarik jendela ke slot monitor, atau double-click untuk slot kosong pertama.")
        hint.setObjectName("Subtle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.window_list = WindowListWidget()
        self.window_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.window_list.itemSelectionChanged.connect(self._update_window_list_labels)
        self.window_list.itemDoubleClicked.connect(self._window_double_clicked)
        layout.addWidget(self.window_list, 1)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(5)
        select_layout = QPushButton("Pilih sesuai layout", objectName="MiniAction")
        select_layout.setToolTip("Pilih sejumlah jendela sesuai jumlah slot layout")
        select_layout.clicked.connect(self._select_windows_for_layout)
        release = QPushButton("Lepas slot", objectName="MiniAction")
        release.setToolTip("Lepaskan jendela terpilih dari slot tanpa menutupnya")
        release.clicked.connect(self._release_selected_slots)
        reset = QPushButton("Reset", objectName="MiniAction")
        reset.setToolTip("Kosongkan semua assignment slot")
        reset.clicked.connect(self._reset_slot_assignments)
        quick_row.addWidget(select_layout, 1)
        quick_row.addWidget(release)
        quick_row.addWidget(reset)
        layout.addLayout(quick_row)
        return side

    def _build_center(self) -> QWidget:
        panel = QFrame(objectName="Card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Monitor Aktif", objectName="SectionTitle"))

        self.monitor_row = QHBoxLayout()
        self.monitor_group = QButtonGroup(self)
        self.monitor_group.setExclusive(True)
        layout.addLayout(self.monitor_row)

        self.preview = MonitorPreview()
        self.preview.slot_clicked.connect(self._preview_slot_clicked)
        self.preview.window_dropped.connect(self._window_dropped_to_slot)
        layout.addWidget(self.preview, 1)

        preview_hint = QLabel(
            "Pilih satu jendela lalu klik slot • pilih beberapa lalu klik slot awal • atau tarik langsung ke slot."
        )
        preview_hint.setObjectName("Subtle")
        preview_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(preview_hint)
        layout.addWidget(QLabel("Pilih Layout", objectName="SectionTitle"))

        preset_row = QHBoxLayout()
        preset_row.setSpacing(7)
        self.layout_group = QButtonGroup(self)
        self.layout_group.setExclusive(True)
        self.layout_buttons: dict[int, LayoutButton] = {}
        for count, label in [
            (2, "2 Jendela"),
            (3, "3 Jendela"),
            (4, "4 Jendela"),
            (6, "6 Jendela"),
            (8, "8 Jendela"),
            (9, "9 Jendela"),
        ]:
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
        layout.addLayout(preset_row)
        return panel

    def _build_settings(self) -> QWidget:
        panel = QFrame(objectName="Card")
        panel.setFixedWidth(335)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(QLabel("Pengaturan Monitor", objectName="SectionTitle"))

        layout.addWidget(QLabel("Resolusi"))
        self.resolution = QComboBox()
        self.resolution.setEnabled(False)
        layout.addWidget(self.resolution)

        layout.addWidget(QLabel("Margin luar"))
        row = QHBoxLayout()
        self.margin_slider = QSlider(Qt.Horizontal)
        self.margin_slider.setRange(0, 60)
        self.margin_slider.setValue(16)
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 60)
        self.margin_spin.setSuffix(" px")
        self.margin_slider.valueChanged.connect(self.margin_spin.setValue)
        self.margin_spin.valueChanged.connect(self.margin_slider.setValue)
        self.margin_spin.valueChanged.connect(self._spacing_changed)
        row.addWidget(self.margin_slider, 1)
        row.addWidget(self.margin_spin)
        layout.addLayout(row)

        layout.addWidget(QLabel("Jarak antar jendela"))
        row2 = QHBoxLayout()
        self.gap_slider = QSlider(Qt.Horizontal)
        self.gap_slider.setRange(0, 50)
        self.gap_slider.setValue(12)
        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(0, 50)
        self.gap_spin.setSuffix(" px")
        self.gap_slider.valueChanged.connect(self.gap_spin.setValue)
        self.gap_spin.valueChanged.connect(self.gap_slider.setValue)
        self.gap_spin.valueChanged.connect(self._spacing_changed)
        row2.addWidget(self.gap_slider, 1)
        row2.addWidget(self.gap_spin)
        layout.addLayout(row2)

        layout.addWidget(QLabel("Area taskbar"))
        self.taskbar_mode = QComboBox()
        self.taskbar_mode.addItems(["Otomatis (Deteksi)", "Gunakan seluruh layar"])
        self.taskbar_mode.currentIndexChanged.connect(self._rebuild_locked_rects)
        layout.addWidget(self.taskbar_mode)
        layout.addWidget(
            QLabel(
                "Secara otomatis menyesuaikan area taskbar\nberdasarkan posisi dan ukuran.",
                objectName="Subtle",
            )
        )

        layout.addSpacing(8)
        lock_row = QHBoxLayout()
        lock_row.addWidget(QLabel("🔒  Kunci layout"))
        lock_row.addStretch()
        self.lock_button = QPushButton("Aktif")
        self.lock_button.setCheckable(True)
        self.lock_button.setChecked(True)
        self.lock_button.setFixedWidth(80)
        self.lock_button.toggled.connect(self._lock_toggled)
        lock_row.addWidget(self.lock_button)
        layout.addLayout(lock_row)
        layout.addWidget(
            QLabel(
                "Saat aktif, posisi jendela yang sudah disusun\ndikembalikan otomatis jika berubah.",
                objectName="Subtle",
            )
        )
        layout.addStretch()
        return panel

    def _build_actions(self) -> QWidget:
        panel = QFrame(objectName="Card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 10, 16, 12)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Aksi Cepat", objectName="SectionTitle"))
        row = QHBoxLayout()
        row.setSpacing(10)

        arrange = ActionCard("Susun Jendela", "Terapkan layout ke jendela terpilih", "▦", True)
        restore = ActionCard("Pulihkan Layout", "Kembalikan workspace tersimpan", "↻")
        save = ActionCard("Simpan Workspace", "Simpan layout saat ini", "▣")
        move = ActionCard("Pindahkan ke Slot", "Pilih jendela dan slot tujuan", "→")
        arrange.clicked.connect(self.arrange_windows)
        restore.clicked.connect(self.restore_workspace)
        save.clicked.connect(self.save_workspace)
        move.clicked.connect(self.move_selected_to_slot)
        for widget in (arrange, restore, save, move):
            row.addWidget(widget, 1)
        layout.addLayout(row)
        return panel

    def _refresh_monitors(self, *_args):
        old_count = len(self.monitor_buttons)
        while self.monitor_row.count():
            item = self.monitor_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.monitor_buttons.clear()
        screens = QApplication.screens()
        self.selected_monitor = min(self.selected_monitor, max(0, len(screens) - 1))
        for index, screen in enumerate(screens):
            geo = screen.geometry()
            suffix = "Utama " if screen == QApplication.primaryScreen() else ""
            btn = QPushButton(
                f"▣  Monitor {index + 1}\n    {suffix}({geo.width()} × {geo.height()})",
                objectName="MonitorTab",
            )
            btn.setCheckable(True)
            btn.setChecked(index == self.selected_monitor)
            btn.clicked.connect(partial(self._select_monitor, index))
            self.monitor_group.addButton(btn)
            self.monitor_row.addWidget(btn)
            self.monitor_buttons.append(btn)

        placeholder = QPushButton("＋  Tambah / Monitor lain", objectName="MonitorTab")
        placeholder.setToolTip("Monitor baru akan muncul otomatis ketika terdeteksi Windows.")
        placeholder.clicked.connect(
            lambda: QMessageBox.information(
                self,
                "Monitor",
                "Hubungkan monitor tambahan ke Windows. Bagi Layar akan mendeteksinya otomatis.",
            )
        )
        self.monitor_row.addWidget(placeholder)
        self._update_resolution()
        self.status_left.setText(f"●  {len(screens)} monitor terdeteksi")
        if old_count and old_count != len(screens):
            self.status_label.setText("Konfigurasi monitor berubah dan sudah diperbarui")

    def _select_monitor(self, index: int):
        self.selected_monitor = index
        for i, button in enumerate(self.monitor_buttons):
            button.setChecked(i == index)
        self._update_resolution()
        self._rebuild_locked_rects()

    def _update_resolution(self):
        screens = QApplication.screens()
        if not screens:
            return
        self.selected_monitor = min(self.selected_monitor, len(screens) - 1)
        geo = screens[self.selected_monitor].geometry()
        self.resolution.clear()
        self.resolution.addItem(f"{geo.width()} × {geo.height()} (Deteksi)")

    def _select_layout(self, count: int):
        self.layout_count = count
        self.custom_shape = None
        self.preview.set_layout_count(
            count,
            margin=self.margin_spin.value(),
            gap=self.gap_spin.value(),
        )
        for c, button in self.layout_buttons.items():
            button.setChecked(c == count)
        self._trim_assignments()
        self._rebuild_locked_rects()

    def _select_custom(self, _ignored=0):
        rows, ok = QInputDialog.getInt(self, "Layout Kustom", "Jumlah baris:", 2, 1, 6)
        if not ok:
            return
        cols, ok = QInputDialog.getInt(self, "Layout Kustom", "Jumlah kolom:", 3, 1, 8)
        if not ok:
            return
        self.custom_shape = (rows, cols)
        self.layout_count = rows * cols
        self.preview.set_layout_count(
            self.layout_count,
            self.custom_shape,
            self.margin_spin.value(),
            self.gap_spin.value(),
        )
        self.layout_buttons[0].setChecked(True)
        self._trim_assignments()
        self._rebuild_locked_rects()

    def _spacing_changed(self, _value: int):
        self.preview.set_spacing(self.margin_spin.value(), self.gap_spin.value())
        self._rebuild_locked_rects()

    def refresh_windows(self):
        selected_handles = (
            {int(item.data(Qt.UserRole)) for item in self.window_list.selectedItems()}
            if hasattr(self, "window_list")
            else set()
        )
        app_handle = int(self.winId()) if IS_WINDOWS else None
        self.windows = list_windows(app_handle)
        self.window_list.clear()

        for win in self.windows:
            slot = self._slot_for_handle(win.handle)
            suffix = f"Slot {slot + 1}" if slot is not None else "Belum ditetapkan"
            item = QListWidgetItem(f"▣   {win.title}\n      {suffix}")
            item.setData(Qt.UserRole, win.handle)
            self.window_list.addItem(item)
            if win.handle in selected_handles:
                item.setSelected(True)

        if self.windows and not self.window_list.selectedItems():
            for index in range(min(self.layout_count, self.window_list.count())):
                self.window_list.item(index).setSelected(True)

        self.status_left.setText(
            f"●  {len(QApplication.screens())} monitor terdeteksi • {len(self.windows)} jendela aktif"
        )
        self._update_preview_assignments()

    def _selected_windows(self) -> list[WindowInfo]:
        handles = [int(item.data(Qt.UserRole)) for item in self.window_list.selectedItems()]
        by_handle = {w.handle: w for w in self.windows}
        return [by_handle[h] for h in handles if h in by_handle]

    def _screen_rect(self) -> Rect:
        screens = QApplication.screens()
        if not screens:
            return Rect(0, 0, 1920, 1080)
        screen = screens[self.selected_monitor]
        qrect = screen.availableGeometry() if self.taskbar_mode.currentIndex() == 0 else screen.geometry()
        return Rect(qrect.x(), qrect.y(), qrect.width(), qrect.height())

    def _targets(self) -> list[Rect]:
        return build_grid(
            self._screen_rect(),
            self.layout_count,
            margin=self.margin_spin.value(),
            gap=self.gap_spin.value(),
            custom_shape=self.custom_shape,
        )

    def arrange_windows(self):
        selected = self._selected_windows()
        if not selected:
            self.refresh_windows()
            selected = self._selected_windows()
        if not selected:
            QMessageBox.warning(
                self,
                "Tidak ada jendela",
                "Tidak ada jendela aplikasi lain yang dipilih atau terdeteksi.",
            )
            return

        targets = self._targets()
        chosen = selected[: len(targets)]
        moved = 0
        self.slot_assignments.clear()
        self.locked_rects.clear()
        for slot, (win, rect) in enumerate(zip(chosen, targets)):
            if move_window(win.handle, rect):
                moved += 1
                self.slot_assignments[slot] = win.handle
                self.locked_rects[win.handle] = rect

        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(
            f"{moved} jendela disusun pada Monitor {self.selected_monitor + 1}"
        )
        if not IS_WINDOWS:
            QMessageBox.information(
                self,
                "Mode pratinjau",
                "Pengaturan jendela sebenarnya hanya aktif di Windows.",
            )

    def _preview_slot_clicked(self, slot: int):
        selected = self._selected_windows()
        if len(selected) == 1:
            self._move_window_to_slot(selected[0], slot)
            return
        if len(selected) > 1:
            self._assign_windows_from_slot(selected, slot)
            return

        handle = self.slot_assignments.get(slot)
        if handle is not None:
            self._select_handle_in_list(handle)
            self.status_label.setText(f"Jendela pada Slot {slot + 1} dipilih")
            return

        QMessageBox.information(
            self,
            "Slot Kosong",
            "Pilih jendela di daftar kiri atau tarik jendela langsung ke slot ini.",
        )

    def _window_dropped_to_slot(self, handle: int, slot: int):
        win = next((w for w in self.windows if w.handle == handle), None)
        if win is None:
            self.refresh_windows()
            win = next((w for w in self.windows if w.handle == handle), None)
        if win is None:
            self.status_label.setText("Jendela yang ditarik sudah tidak tersedia")
            return
        self._select_handle_in_list(handle)
        self._move_window_to_slot(win, slot)

    def _window_double_clicked(self, item: QListWidgetItem, _column: int):
        handle = int(item.data(Qt.UserRole))
        win = next((w for w in self.windows if w.handle == handle), None)
        if win is None:
            return
        empty_slots = [slot for slot in range(len(self._targets())) if slot not in self.slot_assignments]
        if not empty_slots:
            self.status_label.setText("Semua slot sudah terisi")
            return
        self._move_window_to_slot(win, empty_slots[0])

    def _assign_windows_from_slot(self, windows: list[WindowInfo], start_slot: int):
        targets = self._targets()
        moved = 0
        for offset, win in enumerate(windows):
            slot = start_slot + offset
            if slot >= len(targets):
                break
            if self._move_window_to_slot(win, slot, quiet=True):
                moved += 1
        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(
            f"{moved} jendela ditempatkan mulai Slot {start_slot + 1}"
        )

    def _move_window_to_slot(self, win: WindowInfo, slot: int, quiet: bool = False) -> bool:
        targets = self._targets()
        if slot < 0 or slot >= len(targets):
            return False
        if not move_window(win.handle, targets[slot]):
            return False

        for old_slot, handle in list(self.slot_assignments.items()):
            if handle == win.handle or old_slot == slot:
                self.slot_assignments.pop(old_slot, None)
        self.slot_assignments[slot] = win.handle
        self._rebuild_locked_rects()
        if not quiet:
            self._update_preview_assignments()
            self._update_window_list_labels()
            self.status_label.setText(
                f"{win.title[:34]} dipindahkan ke Slot {slot + 1}"
            )
        return True

    def move_selected_to_slot(self):
        selected = self._selected_windows()
        if len(selected) != 1:
            QMessageBox.warning(
                self,
                "Pilih jendela",
                "Pilih tepat satu jendela pada Daftar Jendela terlebih dahulu.",
            )
            return
        targets = self._targets()
        slot, ok = QInputDialog.getInt(
            self,
            "Pindahkan ke Slot",
            f"Nomor slot (1-{len(targets)}):",
            1,
            1,
            len(targets),
        )
        if ok:
            self._move_window_to_slot(selected[0], slot - 1)

    def _select_handle_in_list(self, handle: int):
        self.window_list.clearSelection()
        for index in range(self.window_list.count()):
            item = self.window_list.item(index)
            if int(item.data(Qt.UserRole)) == handle:
                item.setSelected(True)
                self.window_list.setCurrentItem(item)
                self.window_list.scrollToItem(item)
                return

    def _select_windows_for_layout(self):
        self.window_list.clearSelection()
        count = min(self.layout_count, self.window_list.count())
        for index in range(count):
            self.window_list.item(index).setSelected(True)
        self.status_label.setText(f"{count} jendela dipilih sesuai layout")

    def _release_selected_slots(self):
        handles = {int(item.data(Qt.UserRole)) for item in self.window_list.selectedItems()}
        if not handles:
            self.status_label.setText("Pilih jendela yang ingin dilepas dari slot")
            return
        before = len(self.slot_assignments)
        self.slot_assignments = {
            slot: handle
            for slot, handle in self.slot_assignments.items()
            if handle not in handles
        }
        released = before - len(self.slot_assignments)
        self._rebuild_locked_rects()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(f"{released} assignment slot dilepas")

    def _reset_slot_assignments(self):
        count = len(self.slot_assignments)
        self.slot_assignments.clear()
        self.locked_rects.clear()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(f"Slot direset • {count} assignment dibersihkan")

    def _slot_for_handle(self, handle: int) -> int | None:
        for slot, assigned_handle in self.slot_assignments.items():
            if assigned_handle == handle:
                return slot
        return None

    def _trim_assignments(self):
        self.slot_assignments = {
            slot: handle
            for slot, handle in self.slot_assignments.items()
            if slot < self.layout_count
        }
        self._update_preview_assignments()
        self._update_window_list_labels()

    def _update_preview_assignments(self):
        by_handle = {w.handle: w.title for w in self.windows}
        self.preview.set_assignments(
            {
                slot: by_handle.get(handle, "Jendela")
                for slot, handle in self.slot_assignments.items()
            }
        )

    def _update_window_list_labels(self):
        if not hasattr(self, "window_list"):
            return
        by_handle = {w.handle: w for w in self.windows}
        for index in range(self.window_list.count()):
            item = self.window_list.item(index)
            handle = int(item.data(Qt.UserRole))
            win = by_handle.get(handle)
            if not win:
                continue
            slot = self._slot_for_handle(handle)
            suffix = f"Slot {slot + 1}" if slot is not None else "Belum ditetapkan"
            item.setText(f"▣   {win.title}\n      {suffix}")

    def _workspace_payload(self) -> dict:
        by_handle = {w.handle: w for w in self.windows}
        slots = []
        for slot in sorted(self.slot_assignments):
            win = by_handle.get(self.slot_assignments[slot])
            if win:
                slots.append(
                    {
                        "slot": slot,
                        "title": win.title,
                        "class_name": win.class_name,
                    }
                )
        return {
            "monitor_index": self.selected_monitor,
            "layout_count": self.layout_count,
            "custom_shape": list(self.custom_shape) if self.custom_shape else [],
            "margin": self.margin_spin.value(),
            "gap": self.gap_spin.value(),
            "taskbar_mode": self.taskbar_mode.currentIndex(),
            "lock_layout": self.lock_button.isChecked(),
            "slots": slots,
        }

    def save_workspace(self):
        self.storage.save_workspace(self.active_workspace, self._workspace_payload())
        self.saved = self.storage.get_workspace(self.active_workspace)
        self.status_label.setText(
            f'Workspace "{self.active_workspace}" berhasil disimpan'
        )
        self._refresh_workspace_list()

    def restore_workspace(self):
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
        self.slot_assignments.clear()
        by_exact = {(w.title, w.class_name): w for w in self.windows}
        by_title = {w.title: w for w in self.windows}
        targets = self._targets()
        moved = 0
        used_handles: set[int] = set()

        for saved_slot in data.get("slots", []):
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
                moved += 1
                used_handles.add(win.handle)
                self.slot_assignments[slot] = win.handle

        if not self.slot_assignments and isinstance(data.get("window_titles"), list):
            for slot, title in enumerate(data.get("window_titles", [])):
                if slot >= len(targets):
                    break
                win = by_title.get(str(title))
                if win and win.handle not in used_handles and move_window(win.handle, targets[slot]):
                    moved += 1
                    used_handles.add(win.handle)
                    self.slot_assignments[slot] = win.handle

        self._rebuild_locked_rects()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(
            f"Workspace dipulihkan • {moved} jendela diposisikan"
        )

    def _restore_settings(self):
        data = self.saved or {}
        self.selected_monitor = min(
            int(data.get("monitor_index", 0)),
            max(0, len(QApplication.screens()) - 1),
        )
        self.layout_count = int(data.get("layout_count", self.layout_count or 6))
        shape = data.get("custom_shape", [])
        self.custom_shape = tuple(shape) if isinstance(shape, list) and len(shape) == 2 else None
        self.margin_spin.setValue(int(data.get("margin", 16)))
        self.gap_spin.setValue(int(data.get("gap", 12)))
        self.taskbar_mode.setCurrentIndex(int(data.get("taskbar_mode", 0)))
        self.lock_button.setChecked(bool(data.get("lock_layout", True)))
        self._refresh_monitors()

        if self.custom_shape:
            self.preview.set_layout_count(
                self.layout_count,
                self.custom_shape,
                self.margin_spin.value(),
                self.gap_spin.value(),
            )
            self.layout_buttons[0].setChecked(True)
        else:
            self._select_layout(
                self.layout_count if self.layout_count in self.layout_buttons else 6
            )

    def _refresh_workspace_list(self):
        if not hasattr(self, "workspace_list"):
            return
        self.workspace_list.blockSignals(True)
        self.workspace_list.clear()
        names = self.storage.list_workspaces()
        if self.active_workspace not in names:
            names.insert(0, self.active_workspace)
        for name in names:
            item = QListWidgetItem(f"▣   {name}")
            item.setData(Qt.UserRole, name)
            self.workspace_list.addItem(item)
            if name == self.active_workspace:
                self.workspace_list.setCurrentItem(item)
        self.workspace_list.blockSignals(False)

    def _workspace_clicked(self, item: QListWidgetItem):
        name = str(item.data(Qt.UserRole) or "").strip()
        if not name or name == self.active_workspace:
            return
        self.active_workspace = name
        self.storage.set_active_workspace(name)
        self.saved = self.storage.get_workspace(name)
        self.slot_assignments.clear()
        self.locked_rects.clear()
        if self.saved:
            self._restore_settings()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(f"Workspace aktif: {name}")

    def _add_workspace(self):
        existing = set(self.storage.list_workspaces())
        name, ok = QInputDialog.getText(self, "Workspace Baru", "Nama workspace:")
        name = name.strip() if ok else ""
        if not name:
            return
        if name in existing:
            QMessageBox.warning(self, "Workspace", "Nama workspace tersebut sudah ada.")
            return
        self.storage.create_workspace(name)
        self.active_workspace = name
        self.saved = {}
        self.slot_assignments.clear()
        self.locked_rects.clear()
        self._refresh_workspace_list()
        self._update_preview_assignments()
        self.status_label.setText(f"Workspace dibuat: {name}")

    def _lock_toggled(self, checked: bool):
        self.lock_button.setText("Aktif" if checked else "Nonaktif")
        if checked:
            self._rebuild_locked_rects()
            self.status_label.setText("Kunci layout aktif")
        else:
            self.status_label.setText("Kunci layout nonaktif")

    def _rebuild_locked_rects(self, *_args):
        targets = self._targets()
        self.locked_rects = {
            handle: targets[slot]
            for slot, handle in self.slot_assignments.items()
            if 0 <= slot < len(targets)
        }

    def _enforce_lock(self):
        if not self.lock_button.isChecked() or not self.locked_rects:
            return
        stale = []
        for handle, rect in self.locked_rects.items():
            if not window_exists(handle):
                stale.append(handle)
                continue
            move_window(handle, rect)

        if stale:
            stale_set = set(stale)
            self.locked_rects = {
                handle: rect
                for handle, rect in self.locked_rects.items()
                if handle not in stale_set
            }
            self.slot_assignments = {
                slot: handle
                for slot, handle in self.slot_assignments.items()
                if handle not in stale_set
            }
            self._update_preview_assignments()
            self._update_window_list_labels()


def run() -> int:
    from .theme import STYLE

    app = QApplication(sys.argv)
    app.setApplicationName("Bagi Layar")
    app.setOrganizationName("ToniTools")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    return app.exec()
