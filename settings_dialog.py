"""Settings dialog for Daily Task Board.

Purpose (user-facing): choose where the default Excel file (daily_tasks.xlsx) is stored.

- Default: the app folder (same folder as main.py)
- Optional: a custom folder (e.g., OneDrive)
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QLineEdit, QFileDialog, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from icon_utils import load_icon



class SettingsDialog(QDialog):
    def __init__(self, parent=None, project_dir: str = "", mode: str = "project", custom_dir: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(560, 240)

        self._project_dir = project_dir
        self._mode = mode or "project"
        self._custom_dir = custom_dir or ""

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Default Excel file location")
        title.setStyleSheet("font-weight: 800; font-size: 12pt;")
        layout.addWidget(title)

        hint = QLabel(
            "This controls where the app keeps its default workbook (daily_tasks.xlsx).\n"
            "You can keep it in the app folder, or move it to OneDrive/a custom folder."
        )
        hint.setStyleSheet("color: #4b5563;")
        layout.addWidget(hint)

        layout.addSpacing(8)

        box = QFrame()
        box.setFrameShape(QFrame.StyledPanel)
        box.setStyleSheet("QFrame { border: 1px solid #e5e7eb; border-radius: 12px; padding: 10px; }")
        b = QVBoxLayout(box)

        self.rb_project = QRadioButton("Use app folder (recommended)")
        self.rb_project.setChecked(self._mode != "custom")
        b.addWidget(self.rb_project)

        proj_path = QLabel(f"{self._project_dir}")
        proj_path.setStyleSheet("color: #6b7280; margin-left: 22px;")
        b.addWidget(proj_path)

        self.rb_custom = QRadioButton("Use custom folder (e.g., OneDrive)")
        self.rb_custom.setChecked(self._mode == "custom")
        b.addWidget(self.rb_custom)

        row = QHBoxLayout()
        self.custom_edit = QLineEdit(self._custom_dir)
        self.custom_edit.setPlaceholderText("Choose a folder…")
        row.addWidget(self.custom_edit)

        btn_onedrive = QPushButton("Use OneDrive")
        btn_onedrive.setIcon(load_icon("ic_onedrive.png"))
        btn_onedrive.clicked.connect(self._pick_onedrive)
        row.addWidget(btn_onedrive)

        btn_browse = QPushButton("Browse…")
        btn_browse.setIcon(load_icon("ic_open_folder.png"))
        btn_browse.clicked.connect(self._browse)
        row.addWidget(btn_browse)
        b.addLayout(row)

        layout.addWidget(box)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        ok = QPushButton("OK")
        ok.setIcon(load_icon("ic_save.png"))
        ok.setObjectName("PrimaryButton")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.setIcon(load_icon("ic_close.png"))
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        self.rb_project.toggled.connect(self._sync_enabled)
        self.rb_custom.toggled.connect(self._sync_enabled)
        self._sync_enabled()

    def _sync_enabled(self):
        use_custom = self.rb_custom.isChecked()
        self.custom_edit.setEnabled(use_custom)

    def _browse(self):
        start = self.custom_edit.text().strip() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Choose folder", start)
        if folder:
            self.custom_edit.setText(folder)
            self.rb_custom.setChecked(True)

    def _pick_onedrive(self):
        # Common OneDrive environment variables on Windows
        candidates = [
            os.environ.get("OneDrive"),
            os.environ.get("OneDriveConsumer"),
            os.environ.get("OneDriveCommercial"),
        ]
        candidates = [c for c in candidates if c]
        found = None
        for c in candidates:
            p = Path(c)
            if p.exists():
                found = str(p)
                break
        if not found:
            QMessageBox.information(
                self,
                "OneDrive not found",
                "Could not detect OneDrive automatically.\n"
                "Please click 'Browse…' and select your OneDrive folder manually."
            )
            return
        self.custom_edit.setText(found)
        self.rb_custom.setChecked(True)

    def _accept(self):
        if self.rb_project.isChecked():
            self._mode = "project"
            self._custom_dir = ""
            self.accept()
            return

        # Custom
        path = self.custom_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "Invalid folder", "Please choose a folder for the custom location.")
            return
        p = Path(path)
        if not p.exists():
            QMessageBox.warning(self, "Folder not found", "The selected folder does not exist.")
            return
        self._mode = "custom"
        self._custom_dir = str(p)
        self.accept()

    def chosen_mode(self) -> str:
        return self._mode

    def chosen_custom_dir(self) -> str:
        return self._custom_dir
