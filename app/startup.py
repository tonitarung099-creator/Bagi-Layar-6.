from __future__ import annotations

import os
from pathlib import Path
import sys

IS_WINDOWS = os.name == "nt"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Bagi Layar"


def startup_command() -> str:
    """Perintah auto-start untuk build portable maupun mode source."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --tray'

    main_py = Path(__file__).resolve().parents[1] / "main.py"
    return f'"{Path(sys.executable).resolve()}" "{main_py}" --tray'


def current_startup_value() -> str:
    if not IS_WINDOWS:
        return ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
            return str(value or "")
    except Exception:
        return ""


def is_startup_enabled() -> bool:
    value = current_startup_value()
    return bool(value and value == startup_command())


def set_startup_enabled(enabled: bool) -> bool:
    """Aktifkan auto-start di HKCU; tidak membutuhkan hak administrator."""
    if not IS_WINDOWS:
        return False

    try:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(
                    key,
                    VALUE_NAME,
                    0,
                    winreg.REG_SZ,
                    startup_command(),
                )
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False
