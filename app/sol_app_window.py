from __future__ import annotations

from copy import deepcopy
import ctypes
import os
import re
import subprocess
from ctypes import wintypes

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStatusBar,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .app_window import AppMainWindow as LegacyAppMainWindow
from .layouts import Rect
from .multi_monitor import DEFAULT_PROFILE
from .native_display import (
    IS_WINDOWS as NATIVE_WINDOWS,
    native_monitor_for_qscreen,
    native_point_monitor_index,
    qt_rect_from_native,
)
from .reference_widgets import ActionButton, LogoWidget, ReferenceMonitorPreview, ToggleSwitch
from .widgets import LayoutButton, WindowListWidget
from .window_manager import (
    IS_WINDOWS,
    WindowInfo,
    get_window_rect,
    list_windows,
    move_window,
    window_exists,
)
from .window_matcher import find_best_window
from .zone_overlay import WindowDragZoneController


_LEGACY_MONITOR_SUFFIX = re.compile(r"\|\d+x\d+#\d+$", re.IGNORECASE)


def enforce_window_rect(handle: int, rect: Rect) -> bool:
    """Background lock tanpa restore minimize/maximize atau SetWindowPos berulang."""
    if not IS_WINDOWS:
        return False
    current = get_window_rect(handle)
    if current is None:
        return False
    if (
        abs(current.x - rect.x) <= 1
        and abs(current.y - rect.y) <= 1
        and abs(current.width - rect.width) <= 1
        and abs(current.height - rect.height) <= 1
    ):
        return True

    try:
        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(handle)
        # Kunci posisi bukan perintah untuk membatalkan minimize/maximize pengguna.
        if user32.IsIconic(hwnd) or user32.IsZoomed(hwnd):
            return True
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        return bool(
            user32.SetWindowPos(
                hwnd,
                0,
                int(rect.x),
                int(rect.y),
                max(1, int(rect.width)),
                max(1, int(rect.height)),
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
        )
    except Exception:
        return False


class AppMainWindow(LegacyAppMainWindow):
    """Jalur produksi Sol: state multi-monitor konsisten + UI referensi responsif."""

    def __init__(self):
        self._suppressed_saved_slots: set[tuple[str, int]] = set()
        self._saved_slot_intent: dict[str, list[dict]] = {}
        self._screen_signal_ids: set[int] = set()
        self._selected_monitor_key = ""
        super().__init__()
        self.setMinimumSize(1080, 650)
        self._fit_initial_size_to_desktop()
        self._connect_screen_signals()
        self._update_status_bar()

    # ------------------------------------------------------------------
    # UI referensi
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top = QFrame(objectName="TopBar")
        top.setFixedHeight(72)
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(18, 11, 18, 11)
        top_l.setSpacing(11)
        top_l.addWidget(LogoWidget())
        titles = QVBoxLayout()
        titles.setSpacing(1)
        titles.addWidget(QLabel("Bagi Layar", objectName="AppTitle"))
        titles.addWidget(QLabel("Atur jendela, maksimalkan produktivitas.", objectName="AppSub"))
        top_l.addLayout(titles)
        top_l.addStretch()
        gear = QToolButton(objectName="HeaderGear")
        gear.setText("⚙")
        gear.setToolTip("Pengaturan monitor dan layout ada di panel kanan")
        gear.clicked.connect(lambda: self.settings_scroll.setFocus())
        top_l.addWidget(gear)
        outer.addWidget(top)

        body_widget = QWidget()
        body = QHBoxLayout(body_widget)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        content = QWidget()
        content_l = QVBoxLayout(content)
        content_l.setContentsMargins(12, 12, 12, 8)
        content_l.setSpacing(10)
        main_row = QHBoxLayout()
        main_row.setSpacing(10)
        main_row.addWidget(self._build_center(), 1)
        main_row.addWidget(self._build_settings())
        content_l.addLayout(main_row, 1)
        content_l.addWidget(self._build_actions())
        body.addWidget(content, 1)
        outer.addWidget(body_widget, 1)

        status = QStatusBar()
        status.setSizeGripEnabled(True)
        self.setStatusBar(status)
        self.status_left = QLabel("●  Memeriksa monitor…")
        self.status_left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.status_label = QLabel("Siap digunakan   ⓘ")
        self.status_label.setToolTip(
            "Detail tray, hotkey, zona drag, auto-start, dan watcher tersedia dari ikon tray."
        )
        status.addWidget(self.status_left, 1)
        status.addPermanentWidget(self.status_label)

    def _build_sidebar(self) -> QWidget:
        side = QFrame(objectName="Sidebar")
        side.setMinimumWidth(235)
        side.setMaximumWidth(285)
        side.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(13, 13, 13, 10)
        layout.setSpacing(6)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("Workspace", "Kelola layout dan monitor", self._focus_workspace),
            ("Daftar Jendela", "Lihat dan atur jendela aktif", self._focus_windows),
            ("Aksi Cepat", "Jalankan tindakan utama", self._focus_actions),
        ]
        for index, (title, sub, callback) in enumerate(nav_items):
            btn = QPushButton(f"{title}\n{sub}", objectName="NavButton")
            btn.setCheckable(True)
            btn.setChecked(index == 0)
            btn.setFocusPolicy(Qt.StrongFocus)
            btn.clicked.connect(callback)
            self.nav_group.addButton(btn)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addSpacing(6)
        workspace_row = QHBoxLayout()
        workspace_row.addWidget(QLabel("Workspace", objectName="SectionTitle"))
        workspace_row.addStretch()
        add = QToolButton()
        add.setText("+")
        add.setToolTip("Tambah workspace")
        add.clicked.connect(self._add_workspace)
        more = QToolButton()
        more.setText("⋯")
        more.setToolTip("Menu workspace")
        menu = QMenu(more)
        menu.addAction("Simpan Workspace", self.save_workspace)
        menu.addAction("Pulihkan Layout", self.restore_workspace)
        menu.addSeparator()
        menu.addAction("Tambah Workspace", self._add_workspace)
        more.setMenu(menu)
        more.setPopupMode(QToolButton.InstantPopup)
        workspace_row.addWidget(add)
        workspace_row.addWidget(more)
        layout.addLayout(workspace_row)

        self.workspace_list = QListWidget(objectName="WorkspaceList")
        self.workspace_list.setMaximumHeight(132)
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

        self.window_list = WindowListWidget(objectName="WindowList")
        self.window_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.window_list.itemSelectionChanged.connect(self._update_window_list_labels)
        self.window_list.itemDoubleClicked.connect(self._window_double_clicked)
        layout.addWidget(self.window_list, 1)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(5)
        release = QPushButton("Lepas slot", objectName="MiniAction")
        release.clicked.connect(self._release_selected_slots)
        reset = QPushButton("Reset monitor", objectName="MiniAction")
        reset.clicked.connect(self._reset_slot_assignments)
        quick_row.addWidget(release, 1)
        quick_row.addWidget(reset, 1)
        layout.addLayout(quick_row)
        return side

    def _build_center(self) -> QWidget:
        panel = QFrame(objectName="Card")
        panel.setMinimumWidth(430)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)
        layout.addWidget(QLabel("Monitor Aktif", objectName="SectionTitle"))

        monitor_scroll = QScrollArea()
        monitor_scroll.setWidgetResizable(True)
        monitor_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        monitor_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        monitor_scroll.setFixedHeight(72)
        monitor_holder = QWidget()
        self.monitor_row = QHBoxLayout(monitor_holder)
        self.monitor_row.setContentsMargins(0, 0, 0, 0)
        self.monitor_row.setSpacing(7)
        self.monitor_group = QButtonGroup(self)
        self.monitor_group.setExclusive(True)
        monitor_scroll.setWidget(monitor_holder)
        layout.addWidget(monitor_scroll)

        self.preview = ReferenceMonitorPreview()
        self.preview.slot_clicked.connect(self._preview_slot_clicked)
        self.preview.window_dropped.connect(self._window_dropped_to_slot)
        layout.addWidget(self.preview, 1)

        layout.addWidget(QLabel("Pilih Layout", objectName="SectionTitle"))
        preset_scroll = QScrollArea()
        preset_scroll.setWidgetResizable(True)
        preset_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        preset_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        preset_scroll.setFixedHeight(98)
        preset_holder = QWidget()
        preset_row = QHBoxLayout(preset_holder)
        preset_row.setContentsMargins(0, 0, 0, 0)
        preset_row.setSpacing(7)
        self.layout_group = QButtonGroup(self)
        self.layout_group.setExclusive(True)
        self.layout_buttons: dict[int, LayoutButton] = {}
        for count, label in [(2, "2 Jendela"), (3, "3 Jendela"), (4, "4 Jendela"), (6, "6 Jendela"), (8, "8 Jendela"), (9, "9 Jendela")]:
            btn = LayoutButton(count, label)
            btn.setObjectName("LayoutPreset")
            btn.setMinimumWidth(82)
            btn.selected.connect(self._select_layout)
            self.layout_group.addButton(btn)
            self.layout_buttons[count] = btn
            preset_row.addWidget(btn)
        custom = LayoutButton(0, "Kustom")
        custom.setObjectName("LayoutPreset")
        custom.setMinimumWidth(82)
        custom.selected.connect(self._select_custom)
        self.layout_group.addButton(custom)
        self.layout_buttons[0] = custom
        preset_row.addWidget(custom)
        preset_row.addStretch()
        preset_scroll.setWidget(preset_holder)
        layout.addWidget(preset_scroll)
        return panel

    def _setting_label(self, icon: str, text: str) -> QWidget:
        row = QWidget()
        l = QHBoxLayout(row)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(7)
        i = QLabel(icon, objectName="SettingIcon")
        i.setFixedWidth(22)
        l.addWidget(i)
        l.addWidget(QLabel(text, objectName="SettingLabel"), 1)
        return row

    def _build_settings(self) -> QWidget:
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setMinimumWidth(285)
        self.settings_scroll.setMaximumWidth(335)
        panel = QFrame(objectName="Card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 15, 16, 15)
        layout.setSpacing(9)
        layout.addWidget(QLabel("Pengaturan Monitor", objectName="SectionTitle"))

        layout.addWidget(self._setting_label("▭", "Resolusi"))
        self.resolution = QComboBox()
        self.resolution.setEnabled(False)
        layout.addWidget(self.resolution)

        layout.addWidget(self._setting_label("↔", "Margin luar"))
        row = QHBoxLayout()
        self.margin_slider = QSlider(Qt.Horizontal)
        self.margin_slider.setRange(0, 60)
        self.margin_slider.setValue(16)
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 60)
        self.margin_spin.setSuffix(" px")
        self.margin_spin.setFixedWidth(74)
        self.margin_slider.valueChanged.connect(self.margin_spin.setValue)
        self.margin_spin.valueChanged.connect(self.margin_slider.setValue)
        self.margin_spin.valueChanged.connect(self._spacing_changed)
        row.addWidget(self.margin_slider, 1)
        row.addWidget(self.margin_spin)
        layout.addLayout(row)

        layout.addWidget(self._setting_label("⇆", "Jarak antar jendela"))
        row2 = QHBoxLayout()
        self.gap_slider = QSlider(Qt.Horizontal)
        self.gap_slider.setRange(0, 50)
        self.gap_slider.setValue(12)
        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(0, 50)
        self.gap_spin.setSuffix(" px")
        self.gap_spin.setFixedWidth(74)
        self.gap_slider.valueChanged.connect(self.gap_spin.setValue)
        self.gap_spin.valueChanged.connect(self.gap_slider.setValue)
        self.gap_spin.valueChanged.connect(self._spacing_changed)
        row2.addWidget(self.gap_slider, 1)
        row2.addWidget(self.gap_spin)
        layout.addLayout(row2)

        layout.addWidget(self._setting_label("▰", "Area taskbar"))
        self.taskbar_mode = QComboBox()
        self.taskbar_mode.addItems(["Otomatis (Deteksi)", "Gunakan seluruh layar"])
        self.taskbar_mode.currentIndexChanged.connect(self._rebuild_locked_rects)
        layout.addWidget(self.taskbar_mode)
        note = QLabel("Area kerja mengikuti taskbar Windows pada monitor yang dipilih.", objectName="Subtle")
        note.setWordWrap(True)
        layout.addWidget(note)

        separator = QFrame(objectName="SettingSeparator")
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)
        lock_row = QHBoxLayout()
        lock_text = QVBoxLayout()
        lock_text.setSpacing(1)
        lock_text.addWidget(QLabel("Kunci layout", objectName="SettingLabel"))
        lock_note = QLabel("Jaga jendela tetap di slot tanpa membatalkan minimize.", objectName="Subtle")
        lock_note.setWordWrap(True)
        lock_text.addWidget(lock_note)
        lock_row.addLayout(lock_text, 1)
        self.lock_button = ToggleSwitch()
        self.lock_button.setObjectName("LockToggle")
        self.lock_button.setChecked(True)
        self.lock_button.toggled.connect(self._lock_toggled)
        lock_row.addWidget(self.lock_button, 0, Qt.AlignTop)
        layout.addLayout(lock_row)
        layout.addStretch()
        self.settings_scroll.setWidget(panel)
        return self.settings_scroll

    def _build_actions(self) -> QWidget:
        panel = QFrame(objectName="Card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 9, 14, 11)
        layout.setSpacing(7)
        layout.addWidget(QLabel("Aksi Cepat", objectName="SectionTitle"))
        row = QHBoxLayout()
        row.setSpacing(9)
        self.arrange_action = ActionButton("Susun Jendela", "Terapkan layout ke jendela terpilih", "▦", True)
        self.restore_action = ActionButton("Pulihkan Layout", "Kembalikan workspace tersimpan", "↻")
        self.save_action = ActionButton("Simpan Workspace", "Simpan layout saat ini", "▣")
        self.move_action = ActionButton("Pindahkan ke Slot", "Pilih jendela dan slot tujuan", "→")
        self.arrange_action.clicked.connect(self.arrange_windows)
        self.restore_action.clicked.connect(self.restore_workspace)
        self.save_action.clicked.connect(self.save_workspace)
        self.move_action.clicked.connect(self.move_selected_to_slot)
        for widget in (self.arrange_action, self.restore_action, self.save_action, self.move_action):
            row.addWidget(widget, 1)
        layout.addLayout(row)
        return panel

    def _fit_initial_size_to_desktop(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        width = max(1080, min(1566, area.width() - 24))
        height = max(650, min(914, area.height() - 24))
        self.resize(width, height)

    def _focus_workspace(self):
        self.workspace_list.setFocus(Qt.OtherFocusReason)

    def _focus_windows(self):
        self.window_list.setFocus(Qt.OtherFocusReason)

    def _focus_actions(self):
        self.arrange_action.setFocus(Qt.OtherFocusReason)

    # ------------------------------------------------------------------
    # Identitas/topologi monitor stabil
    # ------------------------------------------------------------------
    def _screen_identity_parts(self, screen) -> tuple[str, list[str]]:
        serial = self._safe_screen_value(screen, "serialNumber")
        manufacturer = self._safe_screen_value(screen, "manufacturer")
        model = self._safe_screen_value(screen, "model")
        name = self._safe_screen_value(screen, "name")
        candidates = [v for v in [serial, "|".join(v for v in (manufacturer, model, name) if v), name] if v]
        if serial:
            return f"serial:{serial}", candidates
        if candidates:
            return f"display:{candidates[0]}", candidates
        return "display:unknown", []

    def _screen_key(self, index: int) -> str:
        screens = QApplication.screens()
        if not screens:
            return "display:offline"
        index = max(0, min(index, len(screens) - 1))
        base, _ = self._screen_identity_parts(screens[index])
        same = []
        for i, screen in enumerate(screens):
            other, _ = self._screen_identity_parts(screen)
            if other == base:
                same.append(i)
        if len(same) <= 1:
            return base
        # Fallback ambigu hanya bila driver benar-benar tidak memberi identitas unik.
        # Tidak memakai resolusi/koordinat; workspace tidak digabung diam-diam.
        return f"{base}|ambiguous-{same.index(index) + 1}"

    def _resolve_monitor_key(self, key: str) -> int:
        key = str(key or "")
        screens = QApplication.screens()
        exact = [i for i in range(len(screens)) if self._screen_key(i) == key]
        if len(exact) == 1:
            return exact[0]
        legacy_base = _LEGACY_MONITOR_SUFFIX.sub("", key)
        matches = []
        for i, screen in enumerate(screens):
            _, candidates = self._screen_identity_parts(screen)
            if legacy_base in candidates:
                matches.append(i)
        return matches[0] if len(matches) == 1 else -1

    def _monitor_index_for_key(self, key: str, fallback: int = 0) -> int:
        resolved = self._resolve_monitor_key(key)
        if resolved >= 0:
            return resolved
        try:
            fallback = int(fallback)
        except Exception:
            fallback = 0
        if fallback < 0:
            return -1
        screens = QApplication.screens()
        if not screens:
            return 0
        return max(0, min(fallback, len(screens) - 1))

    def _connected_monitor_index_for_key(self, key: str) -> int:
        return self._resolve_monitor_key(key)

    def _refresh_monitors(self, *_args):
        screens = QApplication.screens()
        previous_key = self._selected_monitor_key
        if not previous_key and screens:
            try:
                previous_key = self._screen_key(min(self.selected_monitor, len(screens) - 1))
            except Exception:
                previous_key = ""

        lock_timer = getattr(self, "lock_timer", None)
        was_active = bool(lock_timer and lock_timer.isActive())
        if was_active:
            lock_timer.stop()

        while self.monitor_row.count():
            item = self.monitor_row.takeAt(0)
            widget = item.widget()
            if widget:
                try:
                    self.monitor_group.removeButton(widget)
                except Exception:
                    pass
                widget.deleteLater()
        self.monitor_buttons.clear()

        if screens:
            resolved = self._resolve_monitor_key(previous_key) if previous_key else -1
            self.selected_monitor = resolved if resolved >= 0 else min(self.selected_monitor, len(screens) - 1)
            for index, screen in enumerate(screens):
                key = self._screen_key(index)
                self.monitor_profiles.setdefault(key, deepcopy(DEFAULT_PROFILE))
                geo = screen.geometry()
                btn = QPushButton(f"Monitor {index + 1}\n{geo.width()} × {geo.height()}", objectName="MonitorTab")
                btn.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
                btn.setIconSize(QSize(24, 24))
                btn.setCheckable(True)
                btn.setChecked(index == self.selected_monitor)
                btn.clicked.connect(lambda _checked=False, i=index: self._select_monitor(i))
                self.monitor_group.addButton(btn)
                self.monitor_row.addWidget(btn)
                self.monitor_buttons.append(btn)
            self._selected_monitor_key = self._screen_key(self.selected_monitor)
            self._activate_assignment_map(self.selected_monitor)
            if hasattr(self, "preview"):
                self._apply_monitor_profile(self.selected_monitor)
        placeholder = QPushButton("Tambah / Monitor Lain", objectName="MonitorPlaceholder")
        placeholder.clicked.connect(self._open_display_settings)
        self.monitor_row.addWidget(placeholder)
        self.monitor_row.addStretch()

        self._migrate_connected_monitor_keys()
        self._rebuild_locked_rects()
        self._update_resolution()
        self._update_monitor_button_labels()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self._connect_screen_signals()
        self._update_status_bar()
        if was_active and lock_timer is not None:
            lock_timer.start(1500)

    def _migrate_connected_monitor_keys(self):
        for old_key in list(self.monitor_profiles):
            index = self._resolve_monitor_key(old_key)
            if index < 0:
                continue
            new_key = self._screen_key(index)
            if new_key == old_key:
                continue
            if new_key not in self.monitor_profiles or self.monitor_profiles[new_key] == DEFAULT_PROFILE:
                self.monitor_profiles[new_key] = self.monitor_profiles[old_key]
            old_assignments = self.monitor_assignments.pop(old_key, None)
            if old_assignments and not self.monitor_assignments.get(new_key):
                self.monitor_assignments[new_key] = old_assignments
            if old_key in self._saved_slot_intent and new_key not in self._saved_slot_intent:
                self._saved_slot_intent[new_key] = self._saved_slot_intent[old_key]

    def _connect_screen_signals(self):
        for screen in QApplication.screens():
            token = id(screen)
            if token in self._screen_signal_ids:
                continue
            self._screen_signal_ids.add(token)
            for name in ("geometryChanged", "availableGeometryChanged", "logicalDotsPerInchChanged"):
                signal = getattr(screen, name, None)
                if signal is not None:
                    try:
                        signal.connect(self._screen_geometry_changed)
                    except Exception:
                        pass

    def _screen_geometry_changed(self, *_args):
        self._rebuild_locked_rects()
        self._update_resolution()
        self._update_monitor_button_labels()
        self._update_status_bar()

    def _select_monitor(self, index: int):
        super()._select_monitor(index)
        if QApplication.screens():
            self._selected_monitor_key = self._screen_key(self.selected_monitor)
        self._update_resolution()
        self._update_status_bar()

    def _update_monitor_button_labels(self):
        screens = QApplication.screens()
        for index, button in enumerate(getattr(self, "monitor_buttons", [])):
            if index >= len(screens):
                continue
            geo = screens[index].geometry()
            prefix = "Utama • " if screens[index] == QApplication.primaryScreen() else ""
            button.setText(f"Monitor {index + 1}\n{prefix}{geo.width()} × {geo.height()}")
            button.setChecked(index == self.selected_monitor)
            button.setToolTip(f"{self._screen_key(index)} • {self._profile_for_monitor(index)['layout_count']} slot")

    def _update_resolution(self):
        screens = QApplication.screens()
        if not screens or not hasattr(self, "resolution"):
            return
        self.selected_monitor = max(0, min(self.selected_monitor, len(screens) - 1))
        screen = screens[self.selected_monitor]
        geo = screen.geometry()
        self.resolution.clear()
        self.resolution.addItem(f"{geo.width()} × {geo.height()} (Deteksi)")
        if hasattr(self, "preview") and hasattr(self.preview, "set_monitor_aspect"):
            self.preview.set_monitor_aspect(geo.width(), geo.height())

    def _screen_rect_for_monitor(self, index: int) -> Rect:
        screens = QApplication.screens()
        if not screens:
            return Rect(0, 0, 1920, 1080)
        index = max(0, min(index, len(screens) - 1))
        screen = screens[index]
        if NATIVE_WINDOWS:
            native = native_monitor_for_qscreen(screen)
            if native is not None:
                profile = self._profile_for_monitor(index)
                return native.work if int(profile.get("taskbar_mode", 0)) == 0 else native.monitor
        return super()._screen_rect_for_monitor(index)

    def _open_display_settings(self):
        if os.name == "nt":
            try:
                subprocess.Popen("start ms-settings:display", shell=True)
                return
            except Exception:
                pass
        QMessageBox.information(self, "Monitor", "Buka pengaturan Display Windows untuk menghubungkan atau mengatur monitor lain.")

    # ------------------------------------------------------------------
    # Assignment + lock: satu jalur untuk semua aksi
    # ------------------------------------------------------------------
    def _move_window_to_slot(self, win: WindowInfo, slot: int, quiet: bool = False) -> bool:
        targets = self._targets()
        if slot < 0 or slot >= len(targets):
            return False
        target = targets[slot]
        if not move_window(win.handle, target):
            return False
        # State lama baru dilepas setelah move sukses.
        self._remove_handle_from_all_monitors(win.handle)
        self.slot_assignments.pop(slot, None)
        self.slot_assignments[slot] = win.handle
        key = self._screen_key(self.selected_monitor)
        self.monitor_assignments[key] = self.slot_assignments
        self._suppressed_saved_slots.discard((key, slot))
        self._rebuild_locked_rects()
        if not quiet:
            self._update_preview_assignments()
            self._update_window_list_labels()
            self.status_label.setText(f"{win.title[:30]} → Monitor {self.selected_monitor + 1}, Slot {slot + 1}")
        return True

    def arrange_windows(self):
        selected = self._selected_windows()
        if not selected:
            self.refresh_windows()
            selected = self._selected_windows()
        if not selected:
            QMessageBox.warning(self, "Tidak ada jendela", "Pilih minimal satu jendela aktif untuk disusun.")
            return
        targets = self._targets()
        chosen = selected[: len(targets)]
        moved = 0
        failed = 0
        for slot, win in enumerate(chosen):
            if self._move_window_to_slot(win, slot, quiet=True):
                moved += 1
            else:
                failed += 1
        self._rebuild_locked_rects()
        self._update_preview_assignments()
        self._update_window_list_labels()
        suffix = f" • {failed} gagal" if failed else ""
        self.status_label.setText(f"{moved} jendela disusun pada Monitor {self.selected_monitor + 1}{suffix}")

    def _release_selected_slots(self):
        handles = {int(item.data(Qt.UserRole)) for item in self.window_list.selectedItems()}
        if not handles:
            self.status_label.setText("Pilih jendela yang ingin dilepas dari slot")
            return
        released = 0
        for key, assignments in self.monitor_assignments.items():
            for slot, handle in list(assignments.items()):
                if handle in handles:
                    assignments.pop(slot, None)
                    self._suppressed_saved_slots.add((str(key), int(slot)))
                    released += 1
        self._activate_assignment_map(self.selected_monitor)
        self._rebuild_locked_rects()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(f"{released} assignment slot dilepas")

    def _reset_slot_assignments(self):
        key = self._screen_key(self.selected_monitor)
        assignments = self.monitor_assignments.setdefault(key, self.slot_assignments)
        count = len(assignments)
        for slot in list(assignments):
            self._suppressed_saved_slots.add((key, int(slot)))
        assignments.clear()
        self._activate_assignment_map(self.selected_monitor)
        self._rebuild_locked_rects()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(f"Monitor {self.selected_monitor + 1} direset • {count} assignment dibersihkan")

    def _rebuild_locked_rects(self, *_args):
        if not getattr(self, "_applying_monitor_profile", False):
            self._capture_current_profile()
        locked: dict[int, Rect] = {}
        screens = QApplication.screens()
        for key, assignments in self.monitor_assignments.items():
            index = self._connected_monitor_index_for_key(str(key))
            if index < 0 or index >= len(screens):
                continue
            profile = self.monitor_profiles.get(str(key), DEFAULT_PROFILE)
            if not bool(profile.get("lock_layout", True)):
                continue
            targets = self._targets_for_monitor(index)
            for slot, handle in assignments.items():
                if 0 <= int(slot) < len(targets):
                    locked[int(handle)] = targets[int(slot)]
        self.locked_rects = locked

    def _enforce_lock(self):
        if not self.locked_rects:
            return
        stale: set[int] = set()
        for handle, rect in list(self.locked_rects.items()):
            if not window_exists(handle):
                stale.add(handle)
                continue
            enforce_window_rect(handle, rect)
        if stale:
            for assignments in self.monitor_assignments.values():
                for slot, handle in list(assignments.items()):
                    if int(handle) in stale:
                        assignments.pop(slot, None)
            self._activate_assignment_map(self.selected_monitor)
            self._rebuild_locked_rects()
            self._update_preview_assignments()
            self._update_window_list_labels()

    # ------------------------------------------------------------------
    # Interaksi dan dialog transaksional
    # ------------------------------------------------------------------
    def _window_double_clicked(self, item: QListWidgetItem):
        handle = int(item.data(Qt.UserRole))
        win = next((w for w in self.windows if w.handle == handle), None)
        if win is None:
            return
        empty_slots = [slot for slot in range(len(self._targets())) if slot not in self.slot_assignments]
        if not empty_slots:
            self.status_label.setText("Semua slot sudah terisi")
            return
        self._move_window_to_slot(win, empty_slots[0])

    def _sync_layout_buttons(self):
        if self.custom_shape:
            for count, button in self.layout_buttons.items():
                button.setChecked(count == 0)
        else:
            selected = self.layout_count if self.layout_count in self.layout_buttons else 6
            for count, button in self.layout_buttons.items():
                button.setChecked(count == selected)

    def _select_custom(self, _ignored=0):
        old_count = self.layout_count
        old_shape = self.custom_shape
        rows, ok = QInputDialog.getInt(self, "Layout Kustom", "Jumlah baris:", 2, 1, 6)
        if not ok:
            self.layout_count, self.custom_shape = old_count, old_shape
            self._sync_layout_buttons()
            return
        cols, ok = QInputDialog.getInt(self, "Layout Kustom", "Jumlah kolom:", 3, 1, 8)
        if not ok:
            self.layout_count, self.custom_shape = old_count, old_shape
            self._sync_layout_buttons()
            return
        self.custom_shape = (rows, cols)
        self.layout_count = rows * cols
        self.preview.set_layout_count(self.layout_count, self.custom_shape, self.margin_spin.value(), self.gap_spin.value())
        self._sync_layout_buttons()
        self._trim_assignments()
        self._capture_current_profile()
        self._rebuild_locked_rects()
        self._update_monitor_button_labels()

    def _add_workspace(self):
        existing = set(self.storage.list_workspaces())
        name, ok = QInputDialog.getText(self, "Workspace Baru", "Nama workspace:")
        if not ok:
            return
        name = str(name).strip()
        if not name:
            return
        if name in existing:
            QMessageBox.warning(self, "Workspace", "Nama workspace tersebut sudah ada.")
            return
        try:
            self.storage.create_workspace(name)
        except Exception as exc:
            QMessageBox.warning(self, "Workspace", f"Workspace gagal dibuat:\n{exc}")
            return
        # Commit state baru hanya setelah create berhasil.
        self.active_workspace = name
        self.saved = {}
        self.monitor_profiles = {self._screen_key(i): deepcopy(DEFAULT_PROFILE) for i in range(len(QApplication.screens()))}
        self.monitor_assignments = {}
        self._saved_slot_intent = {}
        self._suppressed_saved_slots.clear()
        self.selected_monitor = 0
        self._activate_assignment_map(0)
        self._apply_monitor_profile(0)
        self._refresh_workspace_list()
        self._update_preview_assignments()
        self._update_monitor_button_labels()
        self.status_label.setText(f"Workspace dibuat: {name}")

    # ------------------------------------------------------------------
    # Workspace: saved intent terpisah dari live HWND
    # ------------------------------------------------------------------
    def _load_saved_intent(self, data: dict):
        self._saved_slot_intent = {}
        monitors = data.get("monitors") if isinstance(data, dict) else None
        if isinstance(monitors, dict):
            for key, entry in monitors.items():
                if isinstance(entry, dict) and isinstance(entry.get("slots"), list):
                    target_key = str(key)
                    resolved = self._resolve_monitor_key(target_key)
                    if resolved >= 0:
                        target_key = self._screen_key(resolved)
                    self._saved_slot_intent[target_key] = deepcopy(entry.get("slots", []))
        elif isinstance(data, dict) and isinstance(data.get("slots"), list):
            self._saved_slot_intent[self._screen_key(self.selected_monitor)] = deepcopy(data.get("slots", []))

    def _restore_settings(self):
        super()._restore_settings()
        self._load_saved_intent(self.saved or {})
        self._migrate_connected_monitor_keys()
        if QApplication.screens():
            self._selected_monitor_key = self._screen_key(self.selected_monitor)

    def _workspace_payload(self) -> dict:
        payload = super()._workspace_payload()
        payload["workspace_schema"] = 4
        monitors = payload.setdefault("monitors", {})
        saved_monitors = self.saved.get("monitors", {}) if isinstance(self.saved, dict) else {}
        if isinstance(saved_monitors, dict):
            for old_key, old_entry in saved_monitors.items():
                if not isinstance(old_entry, dict):
                    continue
                key = str(old_key)
                resolved = self._resolve_monitor_key(key)
                if resolved >= 0:
                    key = self._screen_key(resolved)
                monitors.setdefault(key, deepcopy(old_entry))

        by_handle = {int(w.handle): w for w in self.windows}
        all_keys = set(monitors) | set(self._saved_slot_intent) | set(self.monitor_assignments)
        for key in all_keys:
            entry = monitors.setdefault(key, deepcopy(self.monitor_profiles.get(key, DEFAULT_PROFILE)))
            preserved: dict[int, dict] = {}
            source_slots = self._saved_slot_intent.get(key)
            if source_slots is None and isinstance(entry.get("slots"), list):
                source_slots = entry.get("slots", [])
            for slot_data in source_slots or []:
                if not isinstance(slot_data, dict):
                    continue
                try:
                    slot = int(slot_data.get("slot", -1))
                except Exception:
                    continue
                if slot >= 0 and (key, slot) not in self._suppressed_saved_slots:
                    preserved[slot] = deepcopy(slot_data)

            for slot, handle in self.monitor_assignments.get(key, {}).items():
                slot = int(slot)
                if (key, slot) in self._suppressed_saved_slots:
                    preserved.pop(slot, None)
                    continue
                win = by_handle.get(int(handle))
                if win is not None:
                    preserved[slot] = {
                        "slot": slot,
                        "title": win.title,
                        "class_name": win.class_name,
                        "process_name": str(getattr(win, "process_name", "") or ""),
                    }
            entry["slots"] = [preserved[s] for s in sorted(preserved)]

        active_key = self._screen_key(self.selected_monitor)
        payload["active_monitor_key"] = active_key
        payload["slots"] = monitors.get(active_key, {}).get("slots", [])
        return payload

    def save_workspace(self):
        try:
            payload = self._workspace_payload()
            self.storage.save_workspace(self.active_workspace, payload)
        except Exception as exc:
            QMessageBox.warning(self, "Simpan Workspace", f"Workspace gagal disimpan:\n{exc}")
            self.status_label.setText("Workspace gagal disimpan")
            return
        self.saved = self.storage.get_workspace(self.active_workspace)
        self._load_saved_intent(self.saved)
        self._suppressed_saved_slots.clear()
        self.status_label.setText(f'Workspace "{self.active_workspace}" berhasil disimpan')
        self._refresh_workspace_list()

    def restore_workspace(self):
        self._suppressed_saved_slots.clear()
        super().restore_workspace()
        self.saved = self.storage.get_workspace(self.active_workspace)
        self._load_saved_intent(self.saved)

    def _workspace_clicked(self, item: QListWidgetItem):
        before = self.active_workspace
        super()._workspace_clicked(item)
        if self.active_workspace != before:
            self._suppressed_saved_slots.clear()
            self._load_saved_intent(self.saved or {})

    def restore_missing_workspace_windows(self) -> tuple[int, int, int]:
        data = self.storage.get_workspace(self.active_workspace)
        if not isinstance(data, dict) or not data:
            return 0, 0, 0
        app_handle = int(self.winId()) if IS_WINDOWS else None
        windows = list_windows(app_handle)
        live_handles = {int(w.handle) for w in windows}

        assignments_changed = False
        for assignments in self.monitor_assignments.values():
            if not isinstance(assignments, dict):
                continue
            for slot, handle in list(assignments.items()):
                if IS_WINDOWS and not window_exists(int(handle)):
                    assignments.pop(slot, None)
                    assignments_changed = True

        used_handles = {
            int(handle)
            for assignments in self.monitor_assignments.values()
            if isinstance(assignments, dict)
            for handle in assignments.values()
            if int(handle) in live_handles or not IS_WINDOWS
        }
        moved = missing = offline = 0
        items, legacy = self._workspace_items(data)
        for saved_key, entry in items:
            if not isinstance(entry, dict):
                continue
            if legacy:
                monitor_index = self.selected_monitor
                current_key = self._screen_key(monitor_index)
            else:
                monitor_index = self._connected_monitor_index_for_key(str(saved_key))
                if monitor_index < 0:
                    offline += 1
                    continue
                current_key = self._screen_key(monitor_index)
            assignments = self.monitor_assignments.setdefault(current_key, {})
            # PENTING: target memakai profile aktif yang sedang diedit, bukan menulis
            # kembali profile tersimpan setiap polling.
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
                if (current_key, slot) in self._suppressed_saved_slots:
                    continue
                if not (0 <= slot < len(targets)):
                    continue
                existing = assignments.get(slot)
                if existing is not None and (int(existing) in live_handles or not IS_WINDOWS):
                    continue
                win = find_best_window(saved_slot, windows, used_handles)
                if win is None:
                    missing += 1
                    continue
                if move_window(win.handle, targets[slot]):
                    self._remove_handle_from_all_monitors(win.handle)
                    assignments[slot] = win.handle
                    used_handles.add(win.handle)
                    moved += 1
                    assignments_changed = True
                else:
                    missing += 1

        if assignments_changed:
            self.windows = windows
            self._activate_assignment_map(self.selected_monitor)
            self._rebuild_locked_rects()
            self._update_preview_assignments()
            self._update_window_list_labels()
        return moved, missing, offline

    # ------------------------------------------------------------------
    # Rekonsiliasi live window + status
    # ------------------------------------------------------------------
    def refresh_windows(self):
        super().refresh_windows()
        if IS_WINDOWS:
            stale: set[int] = set()
            for assignments in self.monitor_assignments.values():
                for handle in assignments.values():
                    if not window_exists(int(handle)):
                        stale.add(int(handle))
            if stale:
                for assignments in self.monitor_assignments.values():
                    for slot, handle in list(assignments.items()):
                        if int(handle) in stale:
                            assignments.pop(slot, None)
                self._activate_assignment_map(self.selected_monitor)
                self._rebuild_locked_rects()
                self._update_preview_assignments()
                self._update_window_list_labels()
        self._update_status_bar()

    def _update_status_bar(self):
        if not hasattr(self, "status_left"):
            return
        screens = QApplication.screens()
        parts = []
        for i, screen in enumerate(screens[:4]):
            geo = screen.geometry()
            marker = "●" if i == self.selected_monitor else "○"
            parts.append(f"{marker} Monitor {i + 1} {geo.width()}×{geo.height()}")
        if len(screens) > 4:
            parts.append(f"+{len(screens) - 4}")
        self.status_left.setText(f"●  {len(screens)} monitor   |   " + "   ".join(parts))


class MultiMonitorDragZoneController(WindowDragZoneController):
    """Overlay drag memakai hit-test native dan konversi per-monitor pada Windows."""

    def _targets_for_screen(self, screen) -> list[Rect]:
        screens = QApplication.screens()
        try:
            index = screens.index(screen)
        except ValueError:
            index = 0
        if hasattr(self.main_window, "_targets_for_monitor"):
            return self.main_window._targets_for_monitor(index)
        return super()._targets_for_screen(screen)

    def _update_overlay(self, cursor_x: int, cursor_y: int) -> None:
        screens = QApplication.screens()
        if NATIVE_WINDOWS:
            monitor_index = native_point_monitor_index(screens, cursor_x, cursor_y)
            if monitor_index >= 0:
                screen = screens[monitor_index]
                targets = self.main_window._targets_for_monitor(monitor_index)
                hover = -1
                for index, target in enumerate(targets):
                    if self._contains(target, cursor_x, cursor_y):
                        hover = index
                        break
                qt_targets = [qt_rect_from_native(screen, target) for target in targets]
                self.monitor_index = monitor_index
                self.targets = targets
                self.hover_slot = hover
                self.overlay.show_zones(screen.geometry(), qt_targets, hover)
                return
        super()._update_overlay(cursor_x, cursor_y)
