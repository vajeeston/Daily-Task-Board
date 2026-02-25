"""Help dialog to display the HTML user manual."""
from __future__ import annotations

from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QTextDocument


class HelpDialog(QDialog):
    """A simple searchable help window that renders the bundled HTML manual."""

    def __init__(self, parent=None, html_path: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Help — User Manual")
        self.setMinimumSize(920, 720)

        self._html_path = html_path

        self._init_ui()
        self._load_manual()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header row
        header = QHBoxLayout()

        title = QLabel("User Manual")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search in manual…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_prev_btn = QPushButton("Prev")
        self.search_next_btn = QPushButton("Next")
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("PrimaryButton")

        header.addWidget(self.search_edit)
        header.addWidget(self.search_prev_btn)
        header.addWidget(self.search_next_btn)
        header.addWidget(self.close_btn)

        layout.addLayout(header)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setReadOnly(True)
        layout.addWidget(self.browser, 1)

        # Signals
        self.close_btn.clicked.connect(self.close)
        self.search_edit.returnPressed.connect(self._find_next)
        self.search_next_btn.clicked.connect(self._find_next)
        self.search_prev_btn.clicked.connect(self._find_prev)

    def _load_manual(self):
        if not self._html_path:
            self.browser.setHtml(
                "<h2>User Manual not found</h2><p>The help file could not be located.</p>"
            )
            return

        p = Path(self._html_path)
        if not p.exists():
            self.browser.setHtml(
                "<h2>User Manual not found</h2><p>The help file could not be located.</p>"
            )
            return

        # Using setSource sets the base URL so relative images (logo) load correctly
        self.browser.setSource(QUrl.fromLocalFile(str(p.resolve())))

    def _find_next(self):
        term = self.search_edit.text().strip()
        if not term:
            return
        # QTextBrowser.find() searches forward by default
        self.browser.find(term)

    def _find_prev(self):
        term = self.search_edit.text().strip()
        if not term:
            return
        # Search backward
        self.browser.find(term, QTextDocument.FindBackward)
