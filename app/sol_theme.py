STYLE = r"""
QMainWindow, QWidget {
    background: #f3f7fc;
    color: #162033;
    font-family: "Segoe UI";
    font-size: 12px;
}
QLabel { background: transparent; }

#TopBar {
    background: #fbfdff;
    border-bottom: 1px solid #dbe5f0;
}
#AppTitle {
    font-size: 20px;
    font-weight: 650;
    color: #121c2c;
}
#AppSub {
    color: #7a8798;
    font-size: 12px;
}
#HeaderGear {
    border: 1px solid #dbe4ef;
    border-radius: 9px;
    background: #ffffff;
    padding: 7px 10px;
    font-size: 16px;
}
#HeaderGear:hover { background: #f3f8ff; border-color: #a9c8ef; }

#Sidebar {
    background: #eef4fb;
    border-right: 1px solid #dce5ef;
}
#NavButton {
    text-align: left;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 8px 11px;
    min-height: 43px;
    background: transparent;
    color: #253247;
}
#NavButton:hover { background: #e7f0fb; }
#NavButton:checked {
    color: #075fd5;
    background: #dceaff;
    border: 1px solid #c7dcfa;
    border-left: 4px solid #0B73FF;
}
#SectionTitle {
    font-weight: 650;
    font-size: 15px;
    color: #172235;
}
#Subtle { color: #7b8797; font-size: 10px; }
#Card {
    background: #ffffff;
    border: 1px solid #dfe7f0;
    border-radius: 14px;
}

#MonitorTab {
    background: #ffffff;
    border: 1px solid #dce5ef;
    border-radius: 10px;
    padding: 8px 12px;
    min-width: 138px;
    min-height: 42px;
    text-align: left;
    color: #263246;
}
#MonitorTab:hover { border-color: #9dc4f4; background: #f9fcff; }
#MonitorTab:checked {
    color: #075fd5;
    background: #eaf3ff;
    border: 1.5px solid #0B73FF;
}
#MonitorPlaceholder {
    background: #fbfdff;
    color: #607089;
    border: 1px dashed #aebed1;
    border-radius: 10px;
    padding: 8px 12px;
    min-width: 150px;
    min-height: 42px;
}
#MonitorPlaceholder:hover { background: #f3f8ff; border-color: #6fa8e9; }

QListWidget {
    background: transparent;
    border: 0;
    outline: 0;
}
QListWidget::item {
    background: #ffffff;
    color: #202b3d;
    border: 1px solid #e0e7ef;
    border-radius: 9px;
    padding: 7px 9px;
    margin: 2px 0;
}
QListWidget::item:hover { background: #f8fbff; border-color: #c9d9ed; }
QListWidget::item:selected {
    color: #0759c4;
    background: #e2efff;
    border-color: #96bdf1;
}
#WorkspaceList::item { min-height: 28px; }
#WindowList::item { min-height: 40px; }

#MiniAction {
    background: #ffffff;
    color: #46566c;
    border: 1px solid #d7e0eb;
    border-radius: 7px;
    padding: 5px 8px;
    font-size: 10px;
}
#MiniAction:hover { color: #075fd5; border-color: #9fc4f4; }

QPushButton#LayoutPreset {
    background: #ffffff;
    border: 1px solid #dce4ed;
    border-radius: 9px;
    padding: 5px;
    color: #313947;
}
QPushButton#LayoutPreset:hover { border-color: #9bc1f4; background: #f9fbff; }
QPushButton#LayoutPreset:checked {
    border: 2px solid #0B73FF;
    background: #eaf3ff;
    color: #075fd5;
}

QComboBox, QSpinBox {
    background: #ffffff;
    border: 1px solid #d4dde8;
    border-radius: 8px;
    padding: 6px 9px;
    min-height: 25px;
    color: #17202d;
}
QComboBox:hover, QSpinBox:hover { border-color: #9abff0; }
QComboBox:disabled { color: #1b2431; background: #fafcff; }
QSlider::groove:horizontal { height: 5px; background: #d8dee7; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #0B73FF;
}
QSlider::sub-page:horizontal { background: #0B73FF; border-radius: 2px; }

#SettingIcon {
    color: #0B73FF;
    font-size: 15px;
    min-width: 22px;
}
#SettingLabel { color: #273449; font-size: 12px; }
#SettingSeparator { background: #e5ebf2; min-height: 1px; max-height: 1px; }

#ActionButton, #ActionPrimaryButton {
    text-align: left;
    border-radius: 11px;
    padding: 12px 15px;
    min-height: 70px;
    font-size: 11px;
}
#ActionButton {
    background: #ffffff;
    color: #253147;
    border: 1px solid #dce4ed;
}
#ActionButton:hover, #ActionButton:focus { background: #fbfdff; border-color: #8fbdf7; }
#ActionButton:pressed { background: #eef6ff; }
#ActionPrimaryButton {
    background: #0B73FF;
    color: #ffffff;
    border: 1px solid #0B73FF;
}
#ActionPrimaryButton:hover, #ActionPrimaryButton:focus { background: #0969e8; border-color: #0969e8; }
#ActionPrimaryButton:pressed { background: #075cc8; }

QToolButton {
    border: 0;
    border-radius: 7px;
    padding: 6px;
    background: transparent;
    color: #26344a;
}
QToolButton:hover { background: #e7f0fb; }
QScrollArea { border: 0; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QStatusBar {
    background: #fbfdff;
    color: #5f6f84;
    border-top: 1px solid #dfe7f0;
    min-height: 34px;
}
QStatusBar QLabel { color: #5f6f84; }
"""