from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .layouts import grid_shape


class MonitorPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.count = 6
        self.custom_shape: tuple[int, int] | None = None
        self.setMinimumHeight(315)

    def set_layout_count(self, count: int, custom_shape: tuple[int, int] | None = None):
        self.count = count
        self.custom_shape = custom_shape
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = self.rect().adjusted(20, 16, -20, -34)
        screen = QRectF(bounds)

        painter.setPen(QPen(QColor("#272b31"), 7))
        painter.setBrush(QColor("#0b0d11"))
        painter.drawRoundedRect(screen, 12, 12)

        inner = screen.adjusted(12, 12, -12, -12)
        rows, cols = self.custom_shape or grid_shape(self.count)
        gap = 5
        cell_w = (inner.width() - gap * (cols - 1)) / cols
        cell_h = (inner.height() - gap * (rows - 1)) / rows
        for i in range(min(self.count, rows * cols)):
            r, c = divmod(i, cols)
            cell = QRectF(
                inner.x() + c * (cell_w + gap),
                inner.y() + r * (cell_h + gap),
                cell_w,
                cell_h,
            )
            painter.setPen(QPen(QColor("#55a5ff"), 1.5))
            painter.setBrush(QColor("#dcecff"))
            painter.drawRoundedRect(cell, 4, 4)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(37, 105, 230, 80))
            painter.drawEllipse(cell.adjusted(cell.width()*0.12, cell.height()*0.18, -cell.width()*0.08, -cell.height()*0.08))
            painter.setBrush(QColor(20, 70, 165, 70))
            painter.drawEllipse(cell.adjusted(cell.width()*0.28, cell.height()*0.10, -cell.width()*0.02, -cell.height()*0.22))

            badge = min(cell.width(), cell.height()) * 0.27
            cx, cy = cell.center().x(), cell.center().y()
            painter.setBrush(QColor(18, 42, 76, 225))
            painter.drawEllipse(QRectF(cx - badge/2, cy - badge/2, badge, badge))
            painter.setPen(QColor("white"))
            font = QFont(self.font())
            font.setBold(True)
            font.setPointSizeF(max(11, badge * 0.24))
            painter.setFont(font)
            painter.drawText(QRectF(cx - badge/2, cy - badge/2, badge, badge), Qt.AlignCenter, str(i + 1))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#4f535a"))
        center_x = screen.center().x()
        bottom = screen.bottom()
        painter.drawRoundedRect(QRectF(center_x - 26, bottom + 5, 52, 18), 3, 3)
        painter.drawRoundedRect(QRectF(center_x - 72, bottom + 22, 144, 8), 4, 4)


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
        if self.count <= 0:
            icon = "□"
        else:
            icon = "▦" if rows > 1 else "▥"
        return f"{icon}\n{label}"


class ActionCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, subtitle: str, icon: str, primary: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("ActionPrimary" if primary else "ActionCard")
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        icon_label = QLabel(icon)
        icon_label.setObjectName("ActionIcon")
        icon_label.setFixedWidth(34)
        layout.addWidget(icon_label)
        text = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("ActionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("ActionSubtitle")
        text.addWidget(title_label)
        text.addWidget(subtitle_label)
        layout.addLayout(text)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
