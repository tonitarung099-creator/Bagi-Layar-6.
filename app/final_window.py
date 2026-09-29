from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .sol_app_window import AppMainWindow as SolAppMainWindow
from .sol_app_window import MultiMonitorDragZoneController


class AppMainWindow(SolAppMainWindow):
    """Lapisan window chrome + tuning geometri untuk UI acuan.

    Engine/state tetap berada di SolAppMainWindow. Lapisan ini hanya menangani
    title bar terintegrasi, resize/move native, ikon fallback, dan ukuran panel
    responsif sehingga perilaku engine tidak tercampur dengan presentasi.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bagi Layar")
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self._chrome_ready = False
        self._chrome_controls: list[QToolButton] = []
        self._install_integrated_chrome()
        self._apply_reference_icons()
        self._apply_responsive_dimensions()

    # ------------------------------------------------------------------
    # Integrated title bar
    # ------------------------------------------------------------------
    def _install_integrated_chrome(self):
        top = self.findChild(QFrame, "TopBar")
        if top is None or top.layout() is None:
            return
        layout = top.layout()
        gear = self.findChild(QToolButton, "HeaderGear")
        if gear is not None:
            layout.removeWidget(gear)

        right = QWidget(top)
        right.setObjectName("WindowChrome")
        right.setFixedWidth(146)
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(1)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(1)
        controls.addStretch()

        minimize = QToolButton(right)
        minimize.setObjectName("WindowControl")
        minimize.setAccessibleName("Minimalkan")
        minimize.setToolTip("Minimalkan")
        minimize.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMinButton))
        minimize.clicked.connect(self.showMinimized)

        maximize = QToolButton(right)
        maximize.setObjectName("WindowControl")
        maximize.setAccessibleName("Maksimalkan atau pulihkan")
        maximize.setToolTip("Maksimalkan / Pulihkan")
        maximize.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        maximize.clicked.connect(self._toggle_maximized)
        self._maximize_button = maximize

        close = QToolButton(right)
        close.setObjectName("WindowCloseControl")
        close.setAccessibleName("Tutup")
        close.setToolTip("Tutup")
        close.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        close.clicked.connect(self.close)

        for button in (minimize, maximize, close):
            button.setFixedSize(38, 27)
            button.setFocusPolicy(Qt.NoFocus)
            controls.addWidget(button)
            self._chrome_controls.append(button)
        right_v.addLayout(controls)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.addStretch()
        if gear is not None:
            gear.setFixedSize(34, 28)
            bottom.addWidget(gear)
        right_v.addLayout(bottom)
        layout.addWidget(right)

        top.setMouseTracking(True)
        top.installEventFilter(self)
        for label in top.findChildren(QLabel):
            label.installEventFilter(self)
        self._title_bar = top
        self._chrome_ready = True

    def _toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_maximize_icon()

    def _sync_maximize_icon(self):
        button = getattr(self, "_maximize_button", None)
        if button is None:
            return
        icon = QStyle.SP_TitleBarNormalButton if self.isMaximized() else QStyle.SP_TitleBarMaxButton
        button.setIcon(self.style().standardIcon(icon))

    def eventFilter(self, watched, event):
        if getattr(self, "_chrome_ready", False):
            top = getattr(self, "_title_bar", None)
            if top is not None and (watched is top or watched in top.findChildren(QLabel)):
                if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                    self._toggle_maximized()
                    return True
                if event.type() == QEvent.MouseButtonPress:
                    if event.button() == Qt.LeftButton:
                        handle = self.windowHandle()
                        if handle is not None and not self.isFullScreen():
                            try:
                                handle.startSystemMove()
                                return True
                            except Exception:
                                pass
                    elif event.button() == Qt.RightButton:
                        self._show_window_menu(event.globalPosition().toPoint())
                        return True
        return super().eventFilter(watched, event)

    def _show_window_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        restore = menu.addAction("Pulihkan")
        restore.setEnabled(self.isMaximized() or self.isMinimized())
        minimize = menu.addAction("Minimalkan")
        maximize = menu.addAction("Maksimalkan")
        maximize.setEnabled(not self.isMaximized())
        menu.addSeparator()
        close = menu.addAction("Tutup")
        chosen = menu.exec(global_pos)
        if chosen is restore:
            self.showNormal()
        elif chosen is minimize:
            self.showMinimized()
        elif chosen is maximize:
            self.showMaximized()
        elif chosen is close:
            self.close()
        self._sync_maximize_icon()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and event.modifiers() & Qt.AltModifier:
            top = getattr(self, "_title_bar", None)
            point = top.mapToGlobal(top.rect().topRight()) if top is not None else self.mapToGlobal(QPoint(20, 20))
            self._show_window_menu(point)
            event.accept()
            return
        super().keyPressEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._sync_maximize_icon()

    def showEvent(self, event):
        super().showEvent(event)
        self._enable_windows_rounded_corners()
        self._apply_responsive_dimensions()

    def nativeEvent(self, event_type, message):
        # Frameless, tetapi resize tetap memakai hit-test native Windows sehingga
        # resize cursor/snap tepi tidak hilang.
        if os.name == "nt" and not self.isMaximized() and not self.isFullScreen():
            try:
                msg = wintypes.MSG.from_address(int(message))
                WM_NCHITTEST = 0x0084
                if msg.message == WM_NCHITTEST:
                    x = ctypes.c_short(msg.lParam & 0xFFFF).value
                    y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    local = self.mapFromGlobal(QPoint(x, y))
                    border = max(6, int(round(6 * self.devicePixelRatioF())))
                    left = local.x() < border
                    right = local.x() >= self.width() - border
                    top = local.y() < border
                    bottom = local.y() >= self.height() - border
                    HTLEFT, HTRIGHT, HTTOP, HTBOTTOM = 10, 11, 12, 15
                    HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT = 13, 14, 16, 17
                    if top and left:
                        return True, HTTOPLEFT
                    if top and right:
                        return True, HTTOPRIGHT
                    if bottom and left:
                        return True, HTBOTTOMLEFT
                    if bottom and right:
                        return True, HTBOTTOMRIGHT
                    if left:
                        return True, HTLEFT
                    if right:
                        return True, HTRIGHT
                    if top:
                        return True, HTTOP
                    if bottom:
                        return True, HTBOTTOM
            except Exception:
                pass
        return super().nativeEvent(event_type, message)

    def _enable_windows_rounded_corners(self):
        if os.name != "nt":
            return
        try:
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(int(self.winId())),
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(DWMWCP_ROUND),
                ctypes.sizeof(DWMWCP_ROUND),
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Reference geometry / icons
    # ------------------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_dimensions()

    def _apply_responsive_dimensions(self):
        side = self.findChild(QFrame, "Sidebar")
        settings = getattr(self, "settings_scroll", None)
        width = max(1, self.width())
        if width >= 1480:
            side_width, settings_width = 285, 346
        elif width >= 1320:
            side_width, settings_width = 255, 315
        else:
            side_width, settings_width = 235, 285

        if side is not None:
            side.setMinimumWidth(side_width)
            side.setMaximumWidth(side_width)
        if settings is not None:
            settings.setMinimumWidth(settings_width)
            settings.setMaximumWidth(settings_width)

        arrange = getattr(self, "arrange_action", None)
        if arrange is not None and arrange.parentWidget() is not None:
            action_panel = arrange.parentWidget()
            action_panel.setMinimumHeight(112)
            action_panel.setMaximumHeight(122)
        for name in ("arrange_action", "restore_action", "save_action", "move_action"):
            button = getattr(self, name, None)
            if button is not None:
                button.setMinimumHeight(62)
                button.setMaximumHeight(70)

    def _apply_reference_icons(self):
        nav = getattr(self, "nav_buttons", [])
        nav_icons = (
            QStyle.SP_DesktopIcon,
            QStyle.SP_FileDialogListView,
            QStyle.SP_BrowserReload,
        )
        for button, icon in zip(nav, nav_icons):
            button.setIcon(self.style().standardIcon(icon))
            button.setIconSize(button.iconSize().expandedTo(button.iconSize()))

        # Fallback generik jendela: tidak menghardcode Chrome. Jika versi engine
        # berikutnya menyediakan ikon proses native, ikon tersebut dapat menimpa ini.
        generic = self.style().standardIcon(QStyle.SP_ComputerIcon)
        for i in range(getattr(self, "window_list", QWidget()).count() if hasattr(self, "window_list") else 0):
            item = self.window_list.item(i)
            if item is not None and item.icon().isNull():
                item.setIcon(generic)

    def refresh_windows(self):
        super().refresh_windows()
        self._apply_reference_icons()
