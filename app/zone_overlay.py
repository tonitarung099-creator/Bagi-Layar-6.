from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .layouts import Rect, build_grid
from .window_manager import (
    IS_WINDOWS,
    WindowInfo,
    get_cursor_position,
    get_foreground_window,
    get_window_rect,
    is_left_button_down,
    window_exists,
)


class ZoneOverlay(QWidget):
    """Overlay click-through yang menggambar zona snap di monitor aktif."""

    def __init__(self, parent=None) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        try:
            flags |= Qt.WindowType.WindowTransparentForInput
        except Exception:
            pass
        super().__init__(parent, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._zones: list[Rect] = []
        self._hover_slot = -1

    def show_zones(self, screen_geometry, zones: list[Rect], hover_slot: int) -> None:
        self._zones = list(zones)
        self._hover_slot = int(hover_slot)
        self.setGeometry(screen_geometry)
        if not self.isVisible():
            self.show()
        self.raise_()
        self.update()

    def hide_zones(self) -> None:
        self._zones = []
        self._hover_slot = -1
        self.hide()

    def paintEvent(self, _event) -> None:
        if not self._zones:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(5, 18, 38, 38))

        origin_x = self.geometry().x()
        origin_y = self.geometry().y()
        for index, zone in enumerate(self._zones):
            rect = QRectF(
                zone.x - origin_x,
                zone.y - origin_y,
                zone.width,
                zone.height,
            ).adjusted(3, 3, -3, -3)
            hovered = index == self._hover_slot

            painter.setPen(
                QPen(
                    QColor("#ffffff" if hovered else "#75b6ff"),
                    3.0 if hovered else 2.0,
                )
            )
            painter.setBrush(
                QColor(20, 120, 245, 185 if hovered else 105)
            )
            painter.drawRoundedRect(rect, 12, 12)

            badge = min(64.0, max(38.0, min(rect.width(), rect.height()) * 0.18))
            badge_rect = QRectF(
                rect.center().x() - badge / 2,
                rect.center().y() - badge / 2,
                badge,
                badge,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(8, 33, 70, 220))
            painter.drawEllipse(badge_rect)
            painter.setPen(QColor("#ffffff"))
            font = QFont(self.font())
            font.setBold(True)
            font.setPointSizeF(max(12.0, badge * 0.28))
            painter.setFont(font)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(index + 1))

        painter.end()


class WindowDragZoneController(QObject):
    """Deteksi drag jendela dan tampilkan zona snap secara otomatis."""

    def __init__(
        self,
        main_window,
        snap_callback: Callable[[WindowInfo, int, int], None],
    ) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.snap_callback = snap_callback
        self.overlay = ZoneOverlay()
        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self._poll)

        self.enabled = bool(IS_WINDOWS)
        self.was_down = False
        self.candidate: WindowInfo | None = None
        self.start_rect: Rect | None = None
        self.last_rect: Rect | None = None
        self.dragging = False
        self.hover_slot = -1
        self.monitor_index = -1
        self.targets: list[Rect] = []
        self._lock_timer_was_active = False

        if self.enabled:
            self.timer.start()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled and IS_WINDOWS)
        if self.enabled:
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()
            self._finish(False)

    @staticmethod
    def _contains(rect: Rect, x: int, y: int) -> bool:
        return (
            rect.x <= x < rect.x + rect.width
            and rect.y <= y < rect.y + rect.height
        )

    def _targets_for_screen(self, screen) -> list[Rect]:
        use_available = self.main_window.taskbar_mode.currentIndex() == 0
        qrect = screen.availableGeometry() if use_available else screen.geometry()
        area = Rect(qrect.x(), qrect.y(), qrect.width(), qrect.height())
        return build_grid(
            area,
            self.main_window.layout_count,
            margin=self.main_window.margin_spin.value(),
            gap=self.main_window.gap_spin.value(),
            custom_shape=self.main_window.custom_shape,
        )

    def _update_overlay(self, cursor_x: int, cursor_y: int) -> None:
        screen = QGuiApplication.screenAt(QPoint(cursor_x, cursor_y))
        if screen is None:
            self.overlay.hide_zones()
            self.hover_slot = -1
            self.monitor_index = -1
            self.targets = []
            return

        screens = QGuiApplication.screens()
        try:
            monitor_index = screens.index(screen)
        except ValueError:
            monitor_index = 0

        targets = self._targets_for_screen(screen)
        hover = -1
        for index, target in enumerate(targets):
            if self._contains(target, cursor_x, cursor_y):
                hover = index
                break

        self.monitor_index = monitor_index
        self.targets = targets
        self.hover_slot = hover
        self.overlay.show_zones(screen.geometry(), targets, hover)

    def _begin(self) -> None:
        self.candidate = get_foreground_window(int(self.main_window.winId()))
        if self.candidate is None:
            return
        self.start_rect = get_window_rect(self.candidate.handle)
        self.last_rect = self.start_rect
        self.dragging = False

    def _movement_looks_like_window_drag(self, current: Rect) -> bool:
        previous = self.last_rect
        if previous is None:
            return False
        moved = abs(current.x - previous.x) + abs(current.y - previous.y)
        resized = abs(current.width - previous.width) + abs(current.height - previous.height)
        return moved >= 3 and resized <= 3

    def _activate_drag(self) -> None:
        if self.dragging:
            return
        self.dragging = True
        lock_timer = getattr(self.main_window, "lock_timer", None)
        if lock_timer is not None:
            self._lock_timer_was_active = lock_timer.isActive()
            if self._lock_timer_was_active:
                lock_timer.stop()

    def _finish(self, allow_snap: bool) -> None:
        candidate = self.candidate
        slot = self.hover_slot
        monitor_index = self.monitor_index

        self.overlay.hide_zones()
        self.candidate = None
        self.start_rect = None
        self.last_rect = None
        was_dragging = self.dragging
        self.dragging = False
        self.hover_slot = -1
        self.monitor_index = -1
        self.targets = []

        lock_timer = getattr(self.main_window, "lock_timer", None)
        if self._lock_timer_was_active and lock_timer is not None:
            lock_timer.start(1500)
        self._lock_timer_was_active = False

        if (
            allow_snap
            and was_dragging
            and candidate is not None
            and slot >= 0
            and monitor_index >= 0
            and window_exists(candidate.handle)
        ):
            self.snap_callback(candidate, slot, monitor_index)

    def _poll(self) -> None:
        if not self.enabled:
            return

        down = is_left_button_down()
        if down and not self.was_down:
            self._begin()

        if down and self.candidate is not None:
            current = get_window_rect(self.candidate.handle)
            if current is None:
                self._finish(False)
                self.was_down = down
                return

            if not self.dragging and self._movement_looks_like_window_drag(current):
                self._activate_drag()

            if self.dragging:
                cursor = get_cursor_position()
                if cursor is not None:
                    self._update_overlay(*cursor)

            self.last_rect = current

        if not down and self.was_down:
            self._finish(True)

        self.was_down = down

    def close(self) -> None:
        self.timer.stop()
        self._finish(False)
        self.overlay.deleteLater()
