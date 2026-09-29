STYLE = r"""
QMainWindow, QWidget {
    background: #f4f8fd;
    color: #10151d;
    font-family: "Segoe UI Variable Text", "Segoe UI";
    font-size: 12px;
}

#TopBar {
    background: #fbfdff;
    border-bottom: 1px solid #dfe7f1;
}
#AppTitle {
    background: transparent;
    font-size: 20px;
    font-weight: 700;
    color: #10151d;
}
#AppSub {
    background: transparent;
    color: #6f7a8c;
    font-size: 11px;
}

#Sidebar {
    background: #eef4fb;
    border-right: 1px solid #dce5ef;
}
#NavButton {
    text-align: left;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 9px 12px;
    font-weight: 600;
    background: transparent;
    color: #1b2533;
}
#NavButton:hover {
    background: #e7f0fc;
}
#NavButton:checked {
    color: #075fd5;
    background: #dceaff;
    border: 1px solid #c9ddfb;
    border-left: 4px solid #1677ff;
}

#SectionTitle {
    background: transparent;
    font-weight: 700;
    font-size: 14px;
    color: #131820;
}
#Subtle {
    background: transparent;
    color: #7b8595;
    font-size: 10px;
}

#Card {
    background: #ffffff;
    border: 1px solid #e0e7f0;
    border-radius: 12px;
}

#MonitorTab {
    background: #ffffff;
    border: 1px solid #dce4ee;
    border-radius: 10px;
    padding: 9px 14px;
    text-align: left;
    min-width: 142px;
    min-height: 42px;
    color: #1a2230;
}
#MonitorTab:hover {
    border-color: #9cc5fa;
    background: #f8fbff;
}
#MonitorTab:checked {
    color: #075fd5;
    background: #eaf3ff;
    border: 1px solid #2d84f6;
    font-weight: 600;
}

QListWidget {
    background: transparent;
    border: 0;
    outline: 0;
}
QListWidget::item {
    background: #ffffff;
    color: #202936;
    border: 1px solid #e1e7ef;
    border-radius: 9px;
    padding: 7px 9px;
    margin: 2px 0;
    min-height: 30px;
}
QListWidget::item:hover {
    background: #f8fbff;
    border-color: #cbdcf2;
}
QListWidget::item:selected {
    color: #064da9;
    background: #dceaff;
    border: 1px solid #8ebaff;
}

QPushButton#LayoutPreset {
    background: #ffffff;
    border: 1px solid #dce4ed;
    border-radius: 9px;
    padding: 5px;
    color: #313947;
    min-width: 82px;
}
QPushButton#LayoutPreset:hover {
    border-color: #9bc1f4;
    background: #f9fbff;
}
QPushButton#LayoutPreset:checked {
    border: 2px solid #2681ff;
    background: #eaf3ff;
    color: #075fd5;
    font-weight: 700;
}

QComboBox, QSpinBox {
    background: #ffffff;
    border: 1px solid #d4dde8;
    border-radius: 8px;
    padding: 6px 9px;
    min-height: 23px;
    color: #17202d;
}
QComboBox:hover, QSpinBox:hover {
    border-color: #9abff0;
}
QComboBox:disabled {
    color: #1b2431;
    background: #fafcff;
}
QComboBox::drop-down {
    width: 26px;
    border: 0;
}

QSlider::groove:horizontal {
    height: 5px;
    background: #d8dee7;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #1779ee;
}
QSlider::sub-page:horizontal {
    background: #1779ee;
    border-radius: 2px;
}

#ActionCard {
    background: #ffffff;
    border: 1px solid #dce4ed;
    border-radius: 10px;
}
#ActionCard:hover {
    border-color: #8fbdf7;
    background: #fbfdff;
}
#ActionPrimary {
    background: #1478f5;
    border: 1px solid #1478f5;
    border-radius: 10px;
}
#ActionPrimary:hover {
    background: #0f6de3;
    border-color: #0f6de3;
}
#ActionPrimary QLabel {
    color: white;
    background: transparent;
}
#ActionTitle {
    background: transparent;
    font-weight: 700;
    font-size: 12px;
}
#ActionSubtitle {
    background: transparent;
    color: #788293;
    font-size: 9px;
}
#ActionPrimary #ActionSubtitle {
    color: #dcecff;
}
#ActionIcon {
    background: transparent;
    font-size: 20px;
    font-weight: 600;
}

QToolButton {
    border: 0;
    border-radius: 7px;
    padding: 6px;
    background: transparent;
    color: #243043;
}
QToolButton:hover {
    background: #e8f1fc;
}

QPushButton {
    outline: 0;
}

QStatusBar {
    background: #fbfdff;
    border-top: 1px solid #e0e7ef;
    color: #596374;
    min-height: 26px;
}
QStatusBar QLabel {
    background: transparent;
    color: #596374;
}

QMessageBox, QInputDialog {
    background: #f7faff;
}
"""
