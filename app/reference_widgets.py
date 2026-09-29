from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QPushButton, QSizePolicy, QWidget

from .widgets import MonitorPreview


class LogoWidget(QWidget):
    """Logo vektor biru-putih agar tidak bergantung pada glyph Unicode."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#0B73FF"))
        p.drawRoundedRect(r, 10, 10)
        p.setBrush(QColor("#ffffff"))
        p.drawRoundedRect(QRectF(9, 10, 22, 15), 3, 3)
        p.setBrush(QColor("#0B73FF"))
        p.drawRect(QRectF(11.5, 12.5, 7, 10))
        p.drawRect(QRectF(21.5, 12.5, 7, 10))
        p.setBrush(QColor("#ffffff"))
        p.drawRoundedRect(QRectF(16, 27, 8, 2.5), 1.2, 1.2)
        p.drawRoundedRect(QRectF(12, 30, 16, 2.5), 1.2, 1.2)


class ToggleSwitch(QAbstractButton):
    """Switch aksesibel: klik/Space mengubah state, thumb putih seperti acuan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(48, 26)
        self.setAccessibleName("Kunci layout")

    def sizeHint(self) -> QSize:
        return QSize(48, 26)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QRectF(self.rect()).adjusted(1, 2, -1, -2)
        if not self.isEnabled():
            bg = QColor("#c9d2df")
        elif self.isChecked():
            bg = QColor("#0B73FF")
        else:
            bg = QColor("#aeb9c8")
        if self.hasFocus():
            p.setPen(QPen(QColor("#78adff"), 1.5))
        else:
            p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(track, 11, 11)
        diameter = 18.0
        x = track.right() - diameter - 2 if self.isChecked() else track.left() + 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(x, track.center().y() - diameter / 2, diameter, diameter))

    def nextCheckState(self):
        super().nextCheckState()
        self.update()


class ActionButton(QPushButton):
    """Kartu aksi semantik berbasis QPushButton; Enter/Space bekerja native."""

    def __init__(self, title: str, subtitle: str, icon: str, primary: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("ActionPrimaryButton" if primary else "ActionButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setText(f"{icon}   {title}\n      {subtitle}")
        self.setAccessibleName(title)
        self.setToolTip(subtitle)


class ReferenceMonitorPreview(MonitorPreview):
    """Preview dengan bezel, stand, rasio monitor, dan wallpaper lipatan biru."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitor_aspect = 16 / 9
        self.setMinimumHeight(250)

    def set_monitor_aspect(self, width: int, height: int):
        if width > 0 and height > 0:
            self.monitor_aspect = max(0.45, min(3.5, width / height))
            self.update()

    def _screen_rect(self) -> QRectF:
        bounds = QRectF(self.rect()).adjusted(18, 12, -18, -38)
        if bounds.width() <= 1 or bounds.height() <= 1:
            return bounds
        target = self.monitor_aspect
        current = bounds.width() / max(1.0, bounds.height())
        if current > target:
            width = bounds.height() * target
            return QRectF(bounds.center().x() - width / 2, bounds.y(), width, bounds.height())
        height = bounds.width() / max(0.01, target)
        return QRectF(bounds.x(), bounds.center().y() - height / 2, bounds.width(), height)

    @staticmethod
    def _wallpaper(painter: QPainter, cell: QRectF, hovered: bool):
        path = QPainterPath()
        path.addRoundedRect(cell, 4, 4)
        painter.save()
        painter.setClipPath(path)

        base = QLinearGradient(cell.topLeft(), cell.bottomRight())
        base.setColorAt(0.0, QColor("#b4dcf7" if hovered else "#9fcdf0"))
        base.setColorAt(0.45, QColor("#4b91da"))
        base.setColorAt(1.0, QColor("#1559b9"))
        painter.fillRect(cell, base)

        # Bentuk lipatan bergaya wallpaper Windows 11, semuanya vektor lokal.
        painter.setPen(Qt.NoPen)
        folds = [
            ("#d4eeff", [(0.02, 0.05), (0.55, 0.18), (0.35, 0.55), (0.00, 0.78)]),
            ("#78b8ee", [(0.55, 0.18), (1.06, 0.04), (0.92, 0.52), (0.35, 0.55)]),
            ("#2f7bd2", [(0.00, 0.78), (0.35, 0.55), (0.64, 1.05), (0.10, 1.02)]),
            ("#0f55bb", [(0.35, 0.55), (0.92, 0.52), (1.03, 0.96), (0.64, 1.05)]),
            ("#5ea4e3", [(0.18, 0.15), (0.57, 0.23), (0.43, 0.47), (0.08, 0.58)]),
        ]
        for color, points in folds:
            poly = QPainterPath()
            first = points[0]
            poly.moveTo(cell.x() + cell.width() * first[0], cell.y() + cell.height() * first[1])
            for px, py in points[1:]:
                poly.lineTo(cell.x() + cell.width() * px, cell.y() + cell.height() * py)
            poly.closeSubpath()
            painter.setBrush(QColor(color))
            painter.drawPath(poly)

        glow = QLinearGradient(cell.topLeft(), cell.bottomRight())
        glow.setColorAt(0.0, QColor(255, 255, 255, 55))
        glow.setColorAt(0.48, QColor(255, 255, 255, 0))
        glow.setColorAt(1.0, QColor(0, 25, 85, 38))
        painter.fillRect(cell, glow)
        painter.restore()
