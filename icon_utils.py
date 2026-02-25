import os
import sys
from pathlib import Path
from PyQt5.QtGui import QIcon

def resource_path(*parts: str) -> Path:
    """Return an absolute path to a bundled resource (works with PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent
    return base.joinpath(*parts)

def load_icon(filename: str) -> QIcon:
    """Load an icon from assets/icons with a safe fallback."""
    p = resource_path("assets", "icons", filename)
    if p.exists():
        return QIcon(str(p))
    return QIcon()
