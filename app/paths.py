from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys

from PySide6.QtCore import QStandardPaths


@lru_cache(maxsize=1)
def application_root() -> Path:
    """Root portable: folder EXE saat frozen, root repo saat mode source."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _is_writable_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".bagi-layar-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def config_dir() -> Path:
    """Utamakan config di folder portable, fallback ke AppConfigLocation."""
    preferred = application_root() / "config"
    if _is_writable_directory(preferred):
        return preferred

    fallback = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    )
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def config_file(name: str) -> Path:
    return config_dir() / name
