import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import STYLE


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Bagi Layar")
    app.setOrganizationName("ToniTools")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))

    win = MainWindow()
    win.workspace_list.setObjectName("WorkspaceList")
    win.window_list.setObjectName("WindowList")
    win.lock_button.setObjectName("LockToggle")

    # Paksa refresh stylesheet setelah objectName khusus diterapkan.
    for widget in (win.workspace_list, win.window_list, win.lock_button):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
