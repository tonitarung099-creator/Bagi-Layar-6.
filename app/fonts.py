from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase


PREFERRED_FAMILIES = (
    "Segoe UI Variable Text",
    "Segoe UI",
    "Arial",
    "Tahoma",
    "Microsoft Sans Serif",
)


def preferred_ui_font(point_size: int = 10) -> QFont:
    """Pilih font Windows yang tersedia tanpa memaketkan/menyalin font pengguna.

    Windows 11 normal akan memilih Segoe UI Variable/Segoe UI. Runner CI atau
    lingkungan minimal yang tidak memilikinya mendapat fallback yang benar-benar
    terpasang, sehingga Qt tidak merender teks menjadi tofu/kotak kosong.
    """
    installed = {name.casefold(): name for name in QFontDatabase.families()}
    for family in PREFERRED_FAMILIES:
        actual = installed.get(family.casefold())
        if actual:
            return QFont(actual, point_size)

    fallback = QFont()
    fallback.setPointSize(point_size)
    return fallback
