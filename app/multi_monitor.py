from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QListWidgetItem, QMessageBox

from .layouts import Rect, build_grid
from .main_window import MainWindow
from .window_manager import WindowInfo, move_window, window_exists
from .zone_overlay import WindowDragZoneController


DEFAULT_PROFILE = {
    "layout_count": 6,
    "custom_shape": [],
    "margin": 16,
    "gap": 12,
    "taskbar_mode": 0,
    "lock_layout": True,
}


class MultiMonitorMainWindow(MainWindow):
    """MainWindow dengan konfigurasi dan assignment slot independen per monitor."""

    def __init__(self):
        self.monitor_profiles: dict[str, dict] = {}
        self.monitor_assignments: dict[str, dict[int, int]] = {}
        self._applying_monitor_profile = False
        super().__init__()
        self._activate_assignment_map(self.selected_monitor)
        self._update_monitor_button_labels()
        self._update_preview_assignments()
        self._update_window_list_labels()

    # ------------------------------------------------------------------
    # Identitas monitor + profile
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_screen_value(screen, name: str) -> str:
        try:
            value = getattr(screen, name)()
            return str(value or "").strip()
        except Exception:
            return ""

    def _screen_key(self, index: int) -> str:
        screens = QApplication.screens()
        if not screens:
            return "monitor-0"
        index = max(0, min(index, len(screens) - 1))
        screen = screens[index]
        geo = screen.geometry()
        name = self._safe_screen_value(screen, "name") or f"Monitor {index + 1}"
        manufacturer = self._safe_screen_value(screen, "manufacturer")
        model = self._safe_screen_value(screen, "model")
        serial = self._safe_screen_value(screen, "serialNumber")
        stable = serial or "|".join(part for part in (manufacturer, model, name) if part)
        if not stable:
            stable = name
        # Resolusi membantu membedakan monitor identik tanpa mengikat ke posisi x/y.
        base = f"{stable}|{geo.width()}x{geo.height()}"
        same_before = 0
        for other in screens[:index]:
            og = other.geometry()
            oname = self._safe_screen_value(other, "name") or "Monitor"
            oman = self._safe_screen_value(other, "manufacturer")
            omodel = self._safe_screen_value(other, "model")
            oserial = self._safe_screen_value(other, "serialNumber")
            ostable = oserial or "|".join(part for part in (oman, omodel, oname) if part) or oname
            if f"{ostable}|{og.width()}x{og.height()}" == base:
                same_before += 1
        return f"{base}#{same_before + 1}"

    def _monitor_index_for_key(self, key: str, fallback: int = 0) -> int:
        screens = QApplication.screens()
        for index in range(len(screens)):
            if self._screen_key(index) == key:
                return index
        if not screens:
            return 0
        return max(0, min(int(fallback), len(screens) - 1))

    @staticmethod
    def _normalize_profile(data: dict | None) -> dict:
        source = data if isinstance(data, dict) else {}
        profile = deepcopy(DEFAULT_PROFILE)
        try:
            profile["layout_count"] = max(1, int(source.get("layout_count", 6)))
        except Exception:
            profile["layout_count"] = 6
        shape = source.get("custom_shape", [])
        if isinstance(shape, (list, tuple)) and len(shape) == 2:
            try:
                rows, cols = max(1, int(shape[0])), max(1, int(shape[1]))
                profile["custom_shape"] = [rows, cols]
                profile["layout_count"] = rows * cols
            except Exception:
                profile["custom_shape"] = []
        try:
            profile["margin"] = max(0, min(60, int(source.get("margin", 16))))
            profile["gap"] = max(0, min(50, int(source.get("gap", 12))))
            profile["taskbar_mode"] = 1 if int(source.get("taskbar_mode", 0)) == 1 else 0
        except Exception:
            pass
        profile["lock_layout"] = bool(source.get("lock_layout", True))
        return profile

    def _legacy_profile(self, data: dict | None = None) -> dict:
        source = data if isinstance(data, dict) else (self.saved or {})
        return self._normalize_profile(source)

    def _load_profiles_from_workspace(self, data: dict) -> None:
        self.monitor_profiles = {}
        monitors = data.get("monitors")
        if isinstance(monitors, dict):
            for key, profile in monitors.items():
                if isinstance(profile, dict):
                    self.monitor_profiles[str(key)] = self._normalize_profile(profile)
        elif isinstance(monitors, list):
            for item in monitors:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key") or "").strip()
                if key:
                    self.monitor_profiles[key] = self._normalize_profile(item)

        if not self.monitor_profiles:
            index = 0
            try:
                index = int(data.get("monitor_index", 0))
            except Exception:
                pass
            key = self._screen_key(index)
            self.monitor_profiles[key] = self._legacy_profile(data)

        for index in range(len(QApplication.screens())):
            key = self._screen_key(index)
            self.monitor_profiles.setdefault(key, deepcopy(DEFAULT_PROFILE))

    def _profile_for_monitor(self, index: int) -> dict:
        key = self._screen_key(index)
        if key not in self.monitor_profiles:
            self.monitor_profiles[key] = deepcopy(DEFAULT_PROFILE)
        return self.monitor_profiles[key]

    def _capture_current_profile(self) -> None:
        if self._applying_monitor_profile or not hasattr(self, "margin_spin"):
            return
        key = self._screen_key(self.selected_monitor)
        self.monitor_profiles[key] = {
            "layout_count": int(self.layout_count),
            "custom_shape": list(self.custom_shape) if self.custom_shape else [],
            "margin": int(self.margin_spin.value()),
            "gap": int(self.gap_spin.value()),
            "taskbar_mode": int(self.taskbar_mode.currentIndex()),
            "lock_layout": bool(self.lock_button.isChecked()),
        }

    def _apply_monitor_profile(self, index: int) -> None:
        screens = QApplication.screens()
        if not screens:
            return
        index = max(0, min(index, len(screens) - 1))
        profile = self._profile_for_monitor(index)
        self._applying_monitor_profile = True
        try:
            self.selected_monitor = index
            self.layout_count = int(profile.get("layout_count", 6))
            shape = profile.get("custom_shape", [])
            self.custom_shape = tuple(shape) if isinstance(shape, list) and len(shape) == 2 else None

            for widget in (self.margin_spin, self.gap_spin, self.taskbar_mode, self.lock_button):
                widget.blockSignals(True)
            self.margin_spin.setValue(int(profile.get("margin", 16)))
            self.margin_slider.setValue(self.margin_spin.value())
            self.gap_spin.setValue(int(profile.get("gap", 12)))
            self.gap_slider.setValue(self.gap_spin.value())
            self.taskbar_mode.setCurrentIndex(int(profile.get("taskbar_mode", 0)))
            self.lock_button.setChecked(bool(profile.get("lock_layout", True)))
            self.lock_button.setText("Aktif" if self.lock_button.isChecked() else "Nonaktif")
            for widget in (self.margin_spin, self.gap_spin, self.taskbar_mode, self.lock_button):
                widget.blockSignals(False)

            self.preview.set_layout_count(
                self.layout_count,
                self.custom_shape,
                self.margin_spin.value(),
                self.gap_spin.value(),
            )
            if self.custom_shape:
                self.layout_buttons[0].setChecked(True)
            else:
                selected = self.layout_count if self.layout_count in self.layout_buttons else 6
                self.layout_count = selected
                for count, button in self.layout_buttons.items():
                    button.setChecked(count == selected)
        finally:
            self._applying_monitor_profile = False
        self._update_resolution()

    # ------------------------------------------------------------------
    # Assignment per monitor
    # ------------------------------------------------------------------
    def _activate_assignment_map(self, index: int) -> None:
        key = self._screen_key(index)
        self.slot_assignments = self.monitor_assignments.setdefault(key, {})

    def _remove_handle_from_all_monitors(self, handle: int) -> None:
        for assignments in self.monitor_assignments.values():
            for slot, assigned in list(assignments.items()):
                if assigned == handle:
                    assignments.pop(slot, None)

    def _assignment_for_handle(self, handle: int) -> tuple[int, int] | None:
        for key, assignments in self.monitor_assignments.items():
            for slot, assigned in assignments.items():
                if assigned == handle:
                    index = self._monitor_index_for_key(key, 0)
                    return index, slot
        return None

    def _slot_for_handle(self, handle: int) -> int | None:
        for slot, assigned_handle in self.slot_assignments.items():
            if assigned_handle == handle:
                return slot
        return None

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
            assigned = self._assignment_for_handle(handle)
            if assigned is None:
                suffix = "Belum ditetapkan"
            else:
                monitor, slot = assigned
                suffix = f"Monitor {monitor + 1} • Slot {slot + 1}"
            item.setText(f"▣   {win.title}\n      {suffix}")

    def _update_preview_assignments(self):
        by_handle = {w.handle: w.title for w in self.windows}
        self.preview.set_assignments(
            {
                slot: by_handle.get(handle, "Jendela")
                for slot, handle in self.slot_assignments.items()
            }
        )

    def _move_window_to_slot(self, win: WindowInfo, slot: int, quiet: bool = False) -> bool:
        targets = self._targets()
        if slot < 0 or slot >= len(targets):
            return False
        if not move_window(win.handle, targets[slot]):
            return False

        self._remove_handle_from_all_monitors(win.handle)
        self.slot_assignments.pop(slot, None)
        self.slot_assignments[slot] = win.handle
        self.monitor_assignments[self._screen_key(self.selected_monitor)] = self.slot_assignments
        self._rebuild_locked_rects()
        if not quiet:
            self._update_preview_assignments()
            self._update_window_list_labels()
            self.status_label.setText(
                f"{win.title[:30]} → Monitor {self.selected_monitor + 1}, Slot {slot + 1}"
            )
        return True

    def _release_selected_slots(self):
        handles = {int(item.data(Qt.UserRole)) for item in self.window_list.selectedItems()}
        if not handles:
            self.status_label.setText("Pilih jendela yang ingin dilepas dari slot")
            return
        released = 0
        for assignments in self.monitor_assignments.values():
            for slot, handle in list(assignments.items()):
                if handle in handles:
                    assignments.pop(slot, None)
                    released += 1
        self._activate_assignment_map(self.selected_monitor)
        self._rebuild_locked_rects()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(f"{released} assignment slot dilepas")

    # ------------------------------------------------------------------
    # Target / layout per monitor
    # ------------------------------------------------------------------
    def _screen_rect_for_monitor(self, index: int) -> Rect:
        screens = QApplication.screens()
        if not screens:
            return Rect(0, 0, 1920, 1080)
        index = max(0, min(index, len(screens) - 1))
        screen = screens[index]
        profile = self._profile_for_monitor(index)
        qrect = screen.availableGeometry() if int(profile.get("taskbar_mode", 0)) == 0 else screen.geometry()
        return Rect(qrect.x(), qrect.y(), qrect.width(), qrect.height())

    def _screen_rect(self) -> Rect:
        return self._screen_rect_for_monitor(self.selected_monitor)

    def _targets_for_monitor(self, index: int) -> list[Rect]:
        profile = self._profile_for_monitor(index)
        shape = profile.get("custom_shape", [])
        custom_shape = tuple(shape) if isinstance(shape, list) and len(shape) == 2 else None
        return build_grid(
            self._screen_rect_for_monitor(index),
            int(profile.get("layout_count", 6)),
            margin=int(profile.get("margin", 16)),
            gap=int(profile.get("gap", 12)),
            custom_shape=custom_shape,
        )

    def _targets(self) -> list[Rect]:
        self._capture_current_profile()
        return self._targets_for_monitor(self.selected_monitor)

    # ------------------------------------------------------------------
    # UI hooks
    # ------------------------------------------------------------------
    def _refresh_monitors(self, *_args):
        previous_index = getattr(self, "selected_monitor", 0)
        super()._refresh_monitors(*_args)
        screens = QApplication.screens()
        if screens:
            self.selected_monitor = max(0, min(previous_index, len(screens) - 1))
            for index in range(len(screens)):
                self.monitor_profiles.setdefault(self._screen_key(index), deepcopy(DEFAULT_PROFILE))
            self._activate_assignment_map(self.selected_monitor)
            if hasattr(self, "preview"):
                self._apply_monitor_profile(self.selected_monitor)
                self._update_preview_assignments()
        self._update_monitor_button_labels()

    def _update_monitor_button_labels(self) -> None:
        if not getattr(self, "monitor_buttons", None):
            return
        screens = QApplication.screens()
        for index, button in enumerate(self.monitor_buttons):
            if index >= len(screens):
                continue
            screen = screens[index]
            geo = screen.geometry()
            profile = self._profile_for_monitor(index)
            suffix = "Utama • " if screen == QApplication.primaryScreen() else ""
            button.setText(
                f"▣  Monitor {index + 1}\n    {suffix}{profile['layout_count']} slot • {geo.width()} × {geo.height()}"
            )
            button.setChecked(index == self.selected_monitor)

    def _select_monitor(self, index: int):
        screens = QApplication.screens()
        if not screens:
            return
        self._capture_current_profile()
        self.monitor_assignments[self._screen_key(self.selected_monitor)] = self.slot_assignments
        index = max(0, min(index, len(screens) - 1))
        self.selected_monitor = index
        self._activate_assignment_map(index)
        self._apply_monitor_profile(index)
        for i, button in enumerate(self.monitor_buttons):
            button.setChecked(i == index)
        self._update_monitor_button_labels()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self._rebuild_locked_rects()
        self.status_label.setText(
            f"Monitor {index + 1} aktif • {self.layout_count} slot"
        )

    def _select_layout(self, count: int):
        super()._select_layout(count)
        self._capture_current_profile()
        self._update_monitor_button_labels()

    def _select_custom(self, _ignored=0):
        super()._select_custom(_ignored)
        self._capture_current_profile()
        self._update_monitor_button_labels()

    def _spacing_changed(self, value: int):
        if self._applying_monitor_profile:
            return
        super()._spacing_changed(value)
        self._capture_current_profile()

    def _lock_toggled(self, checked: bool):
        super()._lock_toggled(checked)
        self._capture_current_profile()
        self._rebuild_locked_rects()

    def _trim_assignments(self):
        self.slot_assignments = {
            slot: handle
            for slot, handle in self.slot_assignments.items()
            if slot < self.layout_count
        }
        self.monitor_assignments[self._screen_key(self.selected_monitor)] = self.slot_assignments
        self._update_preview_assignments()
        self._update_window_list_labels()

    # ------------------------------------------------------------------
    # Lock lintas monitor
    # ------------------------------------------------------------------
    def _rebuild_locked_rects(self, *_args):
        if not self._applying_monitor_profile:
            self._capture_current_profile()
        locked: dict[int, Rect] = {}
        for key, assignments in self.monitor_assignments.items():
            index = self._monitor_index_for_key(key, -1)
            screens = QApplication.screens()
            if not screens or not (0 <= index < len(screens)):
                continue
            profile = self.monitor_profiles.get(key, DEFAULT_PROFILE)
            if not bool(profile.get("lock_layout", True)):
                continue
            targets = self._targets_for_monitor(index)
            for slot, handle in assignments.items():
                if 0 <= slot < len(targets):
                    locked[handle] = targets[slot]
        self.locked_rects = locked

    def _enforce_lock(self):
        if not self.locked_rects:
            return
        stale: set[int] = set()
        for handle, rect in list(self.locked_rects.items()):
            if not window_exists(handle):
                stale.add(handle)
                continue
            move_window(handle, rect)
        if stale:
            for assignments in self.monitor_assignments.values():
                for slot, handle in list(assignments.items()):
                    if handle in stale:
                        assignments.pop(slot, None)
            self._activate_assignment_map(self.selected_monitor)
            self._rebuild_locked_rects()
            self._update_preview_assignments()
            self._update_window_list_labels()

    # ------------------------------------------------------------------
    # Workspace multi-monitor
    # ------------------------------------------------------------------
    def _workspace_payload(self) -> dict:
        self._capture_current_profile()
        self.monitor_assignments[self._screen_key(self.selected_monitor)] = self.slot_assignments
        by_handle = {w.handle: w for w in self.windows}
        monitors: dict[str, dict] = {}
        screens = QApplication.screens()

        # Simpan profile yang pernah dikenal, termasuk monitor yang sedang tidak tersambung.
        for key, profile in self.monitor_profiles.items():
            entry = deepcopy(profile)
            assignments = self.monitor_assignments.get(key, {})
            slots = []
            for slot in sorted(assignments):
                win = by_handle.get(assignments[slot])
                if win:
                    slots.append({
                        "slot": int(slot),
                        "title": win.title,
                        "class_name": win.class_name,
                    })
            entry["slots"] = slots
            monitors[key] = entry

        for index, screen in enumerate(screens):
            key = self._screen_key(index)
            entry = monitors.setdefault(key, deepcopy(self._profile_for_monitor(index)))
            entry["monitor_index"] = index
            entry["name"] = self._safe_screen_value(screen, "name") or f"Monitor {index + 1}"

        current_profile = self._profile_for_monitor(self.selected_monitor)
        return {
            "workspace_schema": 2,
            "active_monitor_key": self._screen_key(self.selected_monitor),
            "active_monitor_index": self.selected_monitor,
            "monitors": monitors,
            # Field legacy dipertahankan agar versi lama aplikasi tetap bisa membaca monitor aktif.
            "monitor_index": self.selected_monitor,
            "layout_count": current_profile["layout_count"],
            "custom_shape": list(current_profile.get("custom_shape", [])),
            "margin": current_profile["margin"],
            "gap": current_profile["gap"],
            "taskbar_mode": current_profile["taskbar_mode"],
            "lock_layout": current_profile["lock_layout"],
            "slots": monitors.get(self._screen_key(self.selected_monitor), {}).get("slots", []),
        }

    def _restore_settings(self):
        data = self.saved or {}
        self.monitor_assignments = {}
        self._load_profiles_from_workspace(data)
        screens = QApplication.screens()
        fallback = int(data.get("active_monitor_index", data.get("monitor_index", 0)) or 0)
        active_key = str(data.get("active_monitor_key") or "")
        if active_key:
            self.selected_monitor = self._monitor_index_for_key(active_key, fallback)
        elif screens:
            self.selected_monitor = max(0, min(fallback, len(screens) - 1))
        else:
            self.selected_monitor = 0
        self._activate_assignment_map(self.selected_monitor)
        self._apply_monitor_profile(self.selected_monitor)
        self._refresh_monitors()
        self._update_monitor_button_labels()

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
        self.monitor_assignments = {
            self._screen_key(index): {} for index in range(len(QApplication.screens()))
        }
        by_exact = {(w.title, w.class_name): w for w in self.windows}
        by_title = {w.title: w for w in self.windows}
        used_handles: set[int] = set()
        moved = 0

        monitors = data.get("monitors")
        if isinstance(monitors, dict):
            items = monitors.items()
        else:
            # Migrasi workspace lama: slot lama dianggap milik monitor aktif.
            key = self._screen_key(self.selected_monitor)
            items = [(key, {**self._legacy_profile(data), "slots": data.get("slots", [])})]

        for saved_key, entry in items:
            if not isinstance(entry, dict):
                continue
            fallback_index = int(entry.get("monitor_index", 0) or 0)
            monitor_index = self._monitor_index_for_key(str(saved_key), fallback_index)
            current_key = self._screen_key(monitor_index)
            # Profile tersimpan mengikuti monitor yang berhasil dicocokkan.
            self.monitor_profiles[current_key] = self._normalize_profile(entry)
            assignments = self.monitor_assignments.setdefault(current_key, {})
            targets = self._targets_for_monitor(monitor_index)
            for saved_slot in entry.get("slots", []):
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
        self.status_label.setText(
            f"Workspace multi-monitor dipulihkan • {moved} jendela diposisikan"
        )

    def _workspace_clicked(self, item: QListWidgetItem):
        name = str(item.data(Qt.UserRole) or "").strip()
        if not name or name == self.active_workspace:
            return
        self._capture_current_profile()
        self.active_workspace = name
        self.storage.set_active_workspace(name)
        self.saved = self.storage.get_workspace(name)
        self.monitor_profiles = {}
        self.monitor_assignments = {}
        self.slot_assignments = {}
        self.locked_rects = {}
        if self.saved:
            self._restore_settings()
        else:
            for index in range(len(QApplication.screens())):
                self.monitor_profiles[self._screen_key(index)] = deepcopy(DEFAULT_PROFILE)
            self._activate_assignment_map(0)
            self._apply_monitor_profile(0)
        self._update_monitor_button_labels()
        self._update_preview_assignments()
        self._update_window_list_labels()
        self.status_label.setText(f"Workspace aktif: {name}")

    def _add_workspace(self):
        super()._add_workspace()
        if self.saved:
            return
        self.monitor_profiles = {}
        self.monitor_assignments = {}
        for index in range(len(QApplication.screens())):
            self.monitor_profiles[self._screen_key(index)] = deepcopy(DEFAULT_PROFILE)
        self.selected_monitor = 0
        self._activate_assignment_map(0)
        self._apply_monitor_profile(0)
        self._update_monitor_button_labels()


class MultiMonitorDragZoneController(WindowDragZoneController):
    """Overlay zona yang memakai profile layout dari monitor di bawah pointer."""

    def _targets_for_screen(self, screen) -> list[Rect]:
        screens = QGuiApplication.screens()
        try:
            index = screens.index(screen)
        except ValueError:
            index = 0
        if hasattr(self.main_window, "_targets_for_monitor"):
            return self.main_window._targets_for_monitor(index)
        return super()._targets_for_screen(screen)
