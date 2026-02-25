#!/usr/bin/env python3
"""
Daily Task Board - Entry Point
Ponniah Vajeeston
Feb 19-2026
"""
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from main_window import MainWindow
from icon_utils import resource_path


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Daily Task Board")
    app.setOrganizationName("DailyTaskBoard")

    # Windows theme (default)
    app.setStyle("WindowsVista")
    icon_path = None
    # Works both in source runs and PyInstaller onefile/onedir.
    for name in ("app_icon.ico", "app_icon.png", "assets/app_icon.ico", "assets/app_icon.png"):
        p = resource_path(*name.split("/"))
        if p.exists():
            icon_path = str(p)
            break
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
