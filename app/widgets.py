from __future__ import annotations

from PySide6.QtCore import QMimeData, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

from .layouts import grid_shape


WINDOW_MIME = "application/x-bagi-layar-window-handle"


class WindowListWidget(QListWidget):
    """Daftar jendela yang dapat ditarik langsung ke preview slot."""

    def __init__(self, parent=None, objectName: str | None = None):
        super().__init__(parent)
        if objectName:
            self.setObjectName(objectName)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.MoveAction)

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if item is None:
            selected = self.selectedItems()
            item = selected[0] if selected else None
        if item is None:
            return

        handle = item.data(Qt.UserRole)
        if handle is None:
            return

        mime = QMimeData()
        mime.setData(WINDOW_MIME, str(int(handle)).encode("ascii"))
        mime.setText(item.text().split("\n", 1)[0])

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)


class MonitorPreview(QWidget):
    """Preview monitor interaktif yang meniru mockup aplikasi."""

    slot_clicked = Signal(int)
    window_dropped = Signal(int, int)  # handle, slot

    def __init__(self, parent=None):
        super().__init__(parent)
        self.count = 6
        self.custom_shape: tuple[int, int] | None = None
        self.margin = 16
        self.gap = 12
        self.assignments: dict[int, str] = {}
        self.hover_slot = -1
        self.drag_active = False
        self.setMinimumHeight(315)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)

    def set_layout_count(
        self,
        count: int,
        custom_shape: tuple[int, int] | None = None,
        margin: int | None = None,
        gap: int | None = None,
    ):
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

    def _screen_rect(self) -> QRectF:
        bounds = self.rect().adjusted(20, 14, -20, -38)
        return QRectF(bounds)

    def _cells(self) -> list[QRectF]:
        screen = self._screen_rect()
        inner = screen.adjusted(12, 12, -12, -12)
        rows, cols = self.custom_shape or grid_shape(self.count)
        preview_margin = min(18.0, self.margin * 0.40)
        preview_gap = min(13.0, max(3.0, self.gap * 0.42))
        inner = inner.adjusted(preview_margin, preview_margin, -preview_margin, -preview_margin)
        cell_w = max(1.0, (inner.width() - preview_gap * (cols - 1)) / cols)
        cell_h = max(1.0, (inner.height() - preview_gap * (rows - 1)) / rows)
        cells: list[QRectF] = []
        for index in range(min(self.count, rows * cols)):
            row, col = divmod(index, cols)
            cells.append(
                QRectF(
                    inner.x() + col * (cell_w + preview_gap),
                    inner.y() + row * (cell_h + preview_gap),
                    cell_w,
                    cell_h,
                )
            )
        return cells

    @staticmethod
    def _wallpaper(painter: QPainter, cell: QRectF, hovered: bool):
        path = QPainterPath()
        path.addRoundedRect(cell, 5, 5)
        painter.save()
        painter.setClipPath(path)

        gradient = QLinearGradient(cell.topLeft(), cell.bottomRight())
        gradient.setColorAt(0.0, QColor("#a7d4f2" if hovered else "#91c1e5"))
        gradient.setColorAt(0.46, QColor("#377fd0"))
        gradient.setColorAt(1.0, QColor("#0759cf"))
        painter.fillRect(cell, gradient)

        waves = [
            (QColor(103, 181, 255, 190), 0.10, 0.48, 0.98, 1.02),
            (QColor(25, 112, 238, 190), 0.02, 0.62, 0.84, 0.92),
            (QColor(12, 70, 190, 170), 0.24, 0.36, 0.98, 0.82),
            (QColor(132, 205, 255, 125), 0.42, 0.10, 1.08, 0.70),
        ]
        painter.setPen(Qt.NoPen)
        for color, left, top, right, bottom in waves:
            painter.setBrush(color)
            r = QRectF(
                cell.x() + cell.width() * left,
                cell.y() + cell.height() * top,
                cell.width() * (right - left),
                cell.height() * (bottom - top),
            )
            painter.drawEllipse(r)

        shine = QLinearGradient(QPointF(cell.left(), cell.top()), QPointF(cell.right(), cell.bottom()))
        shine.setColorAt(0.0, QColor(255, 255, 255, 65))
        shine.setColorAt(0.55, QColor(255, 255, 255, 0))
        shine.setColorAt(1.0, QColor(0, 30, 90, 40))
        painter.fillRect(cell, shine)
        painter.restore()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        screen = self._screen_rect()

        shadow = screen.translated(0, 4).adjusted(-3, -3, 3, 3)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(10, 24, 40, 38))
        painter.drawRoundedRect(shadow, 13, 13)
        painter.setPen(QPen(QColor("#2b2f35"), 7))
        painter.setBrush(QColor("#0b0d11"))
        painter.drawRoundedRect(screen, 11, 11)

        for index, cell in enumerate(self._cells()):
            hovered = index == self.hover_slot
            self._wallpaper(painter, cell, hovered)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#b9ddff" if hovered else "#4ea2ff"), 3.0 if hovered else 1.4))
            painter.drawRoundedRect(cell, 5, 5)

            if hovered and self.drag_active:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(255, 255, 255, 36))
                painter.drawRoundedRect(cell.adjusted(2, 2, -2, -2), 4, 4)

            badge = max(32.0, min(cell.width(), cell.height()) * 0.26)
            cx, cy = cell.center().x(), cell.center().y()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(14, 39, 70, 226))
            painter.drawEllipse(QRectF(cx - badge / 2, cy - badge / 2, badge, badge))
            painter.setPen(QColor("#ffffff"))
            font = QFont(self.font())
            font.setBold(True)
            font.setPointSizeF(max(11, badge * 0.25))
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - badge / 2, cy - badge / 2, badge, badge),
                Qt.AlignCenter,
                str(index + 1),
            )

            label = self.assignments.get(index)
            if label:
                pill = cell.adjusted(8, cell.height() - 29, -8, -6)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(7, 34, 75, 155))
                painter.drawRoundedRect(pill, 6, 6)
                painter.setPen(QColor("#ffffff"))
                small = QFont(self.font())
                small.setPointSizeF(8.2)
                painter.setFont(small)
                painter.drawText(pill.adjusted(7, 0, -7, 0), Qt.AlignCenter | Qt.TextSingleLine, label[:27])

        painter.setPen(Qt.NoPen)
        base_gradient = QLinearGradient(
            QPointF(screen.center().x(), screen.bottom()),
            QPointF(screen.center().x(), screen.bottom() + 30),
        )
        base_gradient.setColorAt(0, QColor("#767b82"))
        base_gradient.setColorAt(1, QColor("#3e4248"))
        painter.setBrush(base_gradient)
        center_x, bottom = screen.center().x(), screen.bottom()
        painter.drawRoundedRect(QRectF(center_x - 25, bottom + 5, 50, 18), 3, 3)
        painter.drawRoundedRect(QRectF(center_x - 72, bottom + 21, 144, 8), 4, 4)

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
        if not self.drag_active:
            self.hover_slot = -1
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            slot = self._slot_at(event.position())
            if slot >= 0:
                self.slot_clicked.emit(slot)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(WINDOW_MIME):
            self.drag_active = True
            self.hover_slot = self._slot_at(event.position())
            event.acceptProposedAction()
            self.update()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat(WINDOW_MIME):
            event.ignore()
            return
        slot = self._slot_at(event.position())
        if slot != self.hover_slot:
            self.hover_slot = slot
            self.update()
        if slot >= 0:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.drag_active = False
        self.hover_slot = -1
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        slot = self._slot_at(event.position())
        try:
            raw = bytes(event.mimeData().data(WINDOW_MIME)).decode("ascii")
            handle = int(raw)
        except (TypeError, ValueError, UnicodeDecodeError):
            event.ignore()
            return

        self.drag_active = False
        self.hover_slot = -1
        self.update()
        if slot < 0:
            event.ignore()
            return

        self.window_dropped.emit(handle, slot)
        event.acceptProposedAction()


class LayoutButton(QPushButton):
    selected = Signal(int)

    def __init__(self, count: int, label: str, parent=None):
        super().__init__(parent)
        self.count = count
        self.label = label
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(82)
        self.setMinimumWidth(88)
        self.setText("")
        self.clicked.connect(lambda: self.selected.emit(self.count))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        selected = self.isChecked()
        hovered = self.underMouse()

        if selected:
            bg, border = QColor("#eaf3ff"), QColor("#2681ff")
            pen_width = 2.0
        elif hovered:
            bg, border = QColor("#f9fbff"), QColor("#9bc1f4")
            pen_width = 1.0
        else:
            bg, border = QColor("#ffffff"), QColor("#dce4ed")
            pen_width = 1.0

        painter.setBrush(bg)
        painter.setPen(QPen(border, pen_width))
        painter.drawRoundedRect(rect, 9, 9)

        icon_area = QRectF(rect.x() + 20, rect.y() + 13, rect.width() - 40, 31)
        icon_color = QColor("#5ba0f8" if selected else "#9aa8ba")
        painter.setPen(Qt.NoPen)
        painter.setBrush(icon_color)

        if self.count <= 0:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(icon_color, 1.5, Qt.DashLine))
            painter.drawRoundedRect(icon_area.adjusted(6, 0, -6, 0), 3, 3)
        else:
            rows, cols = grid_shape(self.count)
            gap = 3.0
            w = (icon_area.width() - gap * (cols - 1)) / cols
            h = (icon_area.height() - gap * (rows - 1)) / rows
            for idx in range(min(self.count, rows * cols)):
                row, col = divmod(idx, cols)
                cell = QRectF(icon_area.x() + col * (w + gap), icon_area.y() + row * (h + gap), w, h)
                painter.drawRoundedRect(cell, 1.6, 1.6)

        painter.setPen(QColor("#075fd5" if selected else "#252e3b"))
        font = QFont(self.font())
        font.setPointSizeF(9.2)
        font.setBold(selected)
        painter.setFont(font)
        painter.drawText(
            QRectF(rect.x() + 3, rect.bottom() - 29, rect.width() - 6, 22),
            Qt.AlignCenter,
            self.label,
        )


class ActionCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, subtitle: str, icon: str, primary: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("ActionPrimary" if primary else "ActionCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(62)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(9)

        icon_label = QLabel(icon)
        icon_label.setObjectName("ActionIcon")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(32, 32)
        layout.addWidget(icon_label)

        text = QVBoxLayout()
        text.setSpacing(1)
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