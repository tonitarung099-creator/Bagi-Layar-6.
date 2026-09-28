from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .layouts import grid_shape


class MonitorPreview(QWidget):
    slot_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.count = 6
        self.custom_shape: tuple[int, int] | None = None
        self.margin = 16
        self.gap = 12
        self.assignments: dict[int, str] = {}
        self.hover_slot = -1
        self.setMinimumHeight(315)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def set_layout_count(self, count: int, custom_shape: tuple[int, int] | None = None, margin: int | None = None, gap: int | None = None):
        self.count = max(1, count)
        self.custom_shape = custom_shape
        if margin is not None:
            self.margin = max(0, margin)
        if gap is not None:
            self.gap = max(0, gap)
        self.update()

    def set_spacing(self, margin: int, gap: int):
        self.margin = max(0, margin)
        self.gap = max(0, gap)
        self.update()

    def set_assignments(self, assignments: dict[int, str]):
        self.assignments = dict(assignments)
        self.update()

    def _cells(self) -> list[QRectF]:
        bounds = self.rect().adjusted(20, 16, -20, -34)
        screen = QRectF(bounds)
        inner = screen.adjusted(12, 12, -12, -12)
        rows, cols = self.custom_shape or grid_shape(self.count)
        preview_margin = min(20.0, self.margin * 0.42)
        preview_gap = min(14.0, max(3.0, self.gap * 0.42))
        inner = inner.adjusted(preview_margin, preview_margin, -preview_margin, -preview_margin)
        cell_w = max(1.0, (inner.width() - preview_gap * (cols - 1)) / cols)
        cell_h = max(1.0, (inner.height() - preview_gap * (rows - 1)) / rows)
        cells: list[QRectF] = []
        for i in range(min(self.count, rows * cols)):
            r, c = divmod(i, cols)
            cells.append(QRectF(inner.x() + c * (cell_w + preview_gap), inner.y() + r * (cell_h + preview_gap), cell_w, cell_h))
        return cells

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = self.rect().adjusted(20, 16, -20, -34)
        screen = QRectF(bounds)
        painter.setPen(QPen(QColor("#272b31"), 7))
        painter.setBrush(QColor("#0b0d11"))
        painter.drawRoundedRect(screen, 12, 12)

        for i, cell in enumerate(self._cells()):
            hovered = i == self.hover_slot
            painter.setPen(QPen(QColor("#87bbff" if hovered else "#55a5ff"), 2.0 if hovered else 1.5))
            painter.setBrush(QColor("#cfe4ff" if hovered else "#dcecff"))
            painter.drawRoundedRect(cell, 5, 5)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(37, 105, 230, 90))
            painter.drawEllipse(cell.adjusted(cell.width()*0.10, cell.height()*0.18, -cell.width()*0.08, -cell.height()*0.08))
            painter.setBrush(QColor(20, 70, 165, 80))
            painter.drawEllipse(cell.adjusted(cell.width()*0.30, cell.height()*0.08, -cell.width()*0.02, -cell.height()*0.24))
            badge = max(30.0, min(cell.width(), cell.height()) * 0.27)
            cx, cy = cell.center().x(), cell.center().y()
            painter.setBrush(QColor(18, 42, 76, 225))
            painter.drawEllipse(QRectF(cx - badge/2, cy - badge/2, badge, badge))
            painter.setPen(QColor("white"))
            font = QFont(self.font()); font.setBold(True); font.setPointSizeF(max(10, badge * 0.24)); painter.setFont(font)
            painter.drawText(QRectF(cx - badge/2, cy - badge/2, badge, badge), Qt.AlignCenter, str(i + 1))
            label = self.assignments.get(i)
            if label:
                painter.setPen(QColor("#10345f"))
                small = QFont(self.font()); small.setPointSizeF(8.5); painter.setFont(small)
                painter.drawText(cell.adjusted(8, cell.height() - 28, -8, -5), Qt.AlignCenter | Qt.TextSingleLine, label[:30])

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#4f535a"))
        center_x = screen.center().x(); bottom = screen.bottom()
        painter.drawRoundedRect(QRectF(center_x - 26, bottom + 5, 52, 18), 3, 3)
        painter.drawRoundedRect(QRectF(center_x - 72, bottom + 22, 144, 8), 4, 4)

    def _slot_at(self, pos) -> int:
        for index, cell in enumerate(self._cells()):
            if cell.contains(pos):
                return index
        return -1

    def mouseMoveEvent(self, event):
        slot = self._slot_at(event.position())
        if slot != self.hover_slot:
            self.hover_slot = slot
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hover_slot = -1
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            slot = self._slot_at(event.position())
            if slot >= 0:
                self.slot_clicked.emit(slot)
        super().mousePressEvent(event)


class LayoutButton(QPushButton):
    selected = Signal(int)

    def __init__(self, count: int, label: str, parent=None):
        super().__init__(parent)
        self.count = count
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(82)
        self.setText(self._make_text(label))
        self.clicked.connect(lambda: self.selected.emit(self.count))

    def _make_text(self, label: str) -> str:
        rows, _cols = grid_shape(self.count if self.count > 0 else 6)
        icon = "□" if self.count <= 0 else ("▦" if rows > 1 else "▥")
        return f"{icon}\n{label}"


class ActionCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, subtitle: str, icon: str, primary: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("ActionPrimary" if primary else "ActionCard")
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self); layout.setContentsMargins(18, 12, 18, 12)
        icon_label = QLabel(icon); icon_label.setObjectName("ActionIcon"); icon_label.setFixedWidth(34); layout.addWidget(icon_label)
        text = QVBoxLayout(); title_label = QLabel(title); title_label.setObjectName("ActionTitle")
        subtitle_label = QLabel(subtitle); subtitle_label.setObjectName("ActionSubtitle")
        text.addWidget(title_label); text.addWidget(subtitle_label); layout.addLayout(text); layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
