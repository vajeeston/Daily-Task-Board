"""
Project dialog for the "Projects" tab.

A project is a lightweight entry for small tools/scripts you build.
Fields:
- Project name
- Status (Unfinished / Working / Postponed / Finished)
- Code location (folder or file path)
- Links (one per line)
- Details (rich text + images/screenshots)
- Attachments (optional paths to related files)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import uuid

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QFileDialog, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QCheckBox, QDateTimeEdit
)
from PyQt5.QtCore import Qt, QDateTime

from icon_utils import load_icon

from models import ProjectItem, TaskStatus


class ProjectDialog(QDialog):
    def __init__(self, parent=None, project: Optional[ProjectItem] = None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Project Details" if project else "New Project")
        self.resize(760, 560)

        self._project = project
        self._init_ui()

        if project:
            self._load(project)

    def _init_ui(self):
        root = QVBoxLayout()

        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Project name (e.g. 'CSV Cleaner', 'Battery Plot Tool')")
        form.addRow("Project:", self.title_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["Study", "Research", "Lab", "Coding", "Personal"])
        self.category_combo.setCurrentText("Coding")
        form.addRow("Category:", self.category_combo)

        self.status_combo = QComboBox()
        self.status_combo.setObjectName("StatusCombo")
        self.status_combo.addItems([s.value for s in TaskStatus])
        self.status_combo.setCurrentText(TaskStatus.UNFINISHED.value)
        self.status_combo.setProperty("taskStatus", self.status_combo.currentText())
        self.status_combo.currentTextChanged.connect(self._sync_status_style)
        form.addRow("Status:", self.status_combo)

        # Optional reminder time
        rem_time_row = QHBoxLayout()
        self.rem_time_enable = QCheckBox("Enable")
        self.rem_time_edit = QDateTimeEdit()
        self.rem_time_edit.setCalendarPopup(True)
        self.rem_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.rem_time_edit.setDateTime(QDateTime.currentDateTime())
        self.rem_time_edit.setEnabled(False)
        rem_time_row.addWidget(self.rem_time_enable)
        rem_time_row.addWidget(self.rem_time_edit, 1)
        form.addRow("Reminder time:", rem_time_row)

        # Reminder options
        rem_row = QHBoxLayout()
        self.rem_at = QCheckBox("At time")
        self.rem_10m = QCheckBox("10 min before")
        self.rem_1h = QCheckBox("1 hour before")
        rem_row.addWidget(self.rem_at)
        rem_row.addWidget(self.rem_10m)
        rem_row.addWidget(self.rem_1h)
        rem_row.addStretch()
        form.addRow("Reminders:", rem_row)

        # Code location + browse
        code_row = QHBoxLayout()
        self.code_path_edit = QLineEdit()
        self.code_path_edit.setPlaceholderText("Folder or main script path (optional)")
        self.browse_code_btn = QPushButton("Browse…")
        self.browse_code_btn.setIcon(load_icon("ic_open_folder.png"))
        self.browse_code_btn.setObjectName("SecondaryButton")
        code_row.addWidget(self.code_path_edit, 1)
        code_row.addWidget(self.browse_code_btn, 0)
        form.addRow("Code location:", code_row)

        # Links
        self.links_edit = QTextEdit()
        self.links_edit.setAcceptRichText(False)
        self.links_edit.setPlaceholderText("Links (one per line)\nExample:\nhttps://github.com/...\nhttps://trello.com/...")
        self.links_edit.setMaximumHeight(90)
        form.addRow("Links:", self.links_edit)

        root.addLayout(form)

        # Details editor
        root.addWidget(QLabel("Details (notes, usage, screenshots):"))
        self.details_edit = QTextEdit()
        self.details_edit.setAcceptRichText(True)
        root.addWidget(self.details_edit, stretch=1)

        # Attachments list
        attach_row = QHBoxLayout()
        attach_row.addWidget(QLabel("Attachments:"))
        self.attach_list = QListWidget()
        self.attach_list.setMaximumHeight(90)
        attach_row.addWidget(self.attach_list, stretch=1)

        attach_btns = QVBoxLayout()
        self.add_attach_btn = QPushButton("Add File")
        self.add_attach_btn.setIcon(load_icon("ic_open.png"))
        self.remove_attach_btn = QPushButton("Remove")
        self.remove_attach_btn.setIcon(load_icon("ic_delete.png"))
        self.add_attach_btn.setObjectName("SecondaryButton")
        self.remove_attach_btn.setObjectName("DangerButton")
        attach_btns.addWidget(self.add_attach_btn)
        attach_btns.addWidget(self.remove_attach_btn)
        attach_btns.addStretch()
        attach_row.addLayout(attach_btns)
        root.addLayout(attach_row)

        # Editor buttons
        editor_btns = QHBoxLayout()
        self.insert_image_btn = QPushButton("Insert Image into Details")
        self.insert_image_btn.setIcon(load_icon("ic_add.png"))
        self.clear_details_btn = QPushButton("Clear Details")
        self.clear_details_btn.setIcon(load_icon("ic_delete.png"))
        self.insert_image_btn.setObjectName("SecondaryButton")
        self.clear_details_btn.setObjectName("SecondaryButton")
        editor_btns.addWidget(self.insert_image_btn)
        editor_btns.addWidget(self.clear_details_btn)
        editor_btns.addStretch()
        root.addLayout(editor_btns)

        # Save/Cancel
        btns = QHBoxLayout()
        btns.addStretch()
        self.save_btn = QPushButton("Save")
        self.save_btn.setIcon(load_icon("ic_save.png"))
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(load_icon("ic_close.png"))
        self.save_btn.setObjectName("PrimaryButton")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.save_btn.setDefault(True)
        btns.addWidget(self.save_btn)
        btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

        self.setLayout(root)

        # connections
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._validate_and_accept)
        self.clear_details_btn.clicked.connect(self.details_edit.clear)
        self.insert_image_btn.clicked.connect(self._insert_image)
        self.add_attach_btn.clicked.connect(self._add_attachment)
        self.remove_attach_btn.clicked.connect(self._remove_attachment)
        self.browse_code_btn.clicked.connect(self._browse_code_location)
        self.rem_time_enable.toggled.connect(self._toggle_rem_time)

    def _toggle_rem_time(self, checked: bool):
        self.rem_time_edit.setEnabled(bool(checked))

    def _sync_status_style(self):
        txt = self.status_combo.currentText()
        self.status_combo.setProperty("taskStatus", txt)
        self.status_combo.style().unpolish(self.status_combo)
        self.status_combo.style().polish(self.status_combo)
        self.status_combo.update()

    def _browse_code_location(self):
        # Let user pick a folder; if they cancel, optionally allow a file pick
        folder = QFileDialog.getExistingDirectory(self, "Select Code Folder")
        if folder:
            self.code_path_edit.setText(folder)
            return
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Main Script/File", "", "All Files (*)")
        if file_name:
            self.code_path_edit.setText(file_name)

    def _insert_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Insert Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if not filename:
            return
        cursor = self.details_edit.textCursor()
        cursor.insertImage(filename)

    def _add_attachment(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Add Attachment", "", "All Files (*)")
        if not filename:
            return
        self.attach_list.addItem(QListWidgetItem(filename))

    def _remove_attachment(self):
        row = self.attach_list.currentRow()
        if row >= 0:
            self.attach_list.takeItem(row)

    def _load(self, p: ProjectItem):
        self.title_edit.setText(p.title)
        self.status_combo.setCurrentText(p.status.value)
        self._sync_status_style()
        self.category_combo.setCurrentText(getattr(p, 'category', 'Coding') or 'Coding')
        self.code_path_edit.setText(p.code_path or "")
        self.links_edit.setPlainText("\n".join(p.links or []))
        if getattr(p, "reminder_dt", None):
            self.rem_time_enable.setChecked(True)
            self.rem_time_edit.setEnabled(True)
            self.rem_time_edit.setDateTime(QDateTime(p.reminder_dt))
        else:
            self.rem_time_enable.setChecked(False)
            self.rem_time_edit.setEnabled(False)

        self.rem_at.setChecked(bool(getattr(p, "remind_at", False)))
        self.rem_10m.setChecked(bool(getattr(p, "remind_10m", False)))
        self.rem_1h.setChecked(bool(getattr(p, "remind_1h", False)))
        self.details_edit.setHtml(p.details_html or "")
        self.attach_list.clear()
        for a in p.attachments:
            self.attach_list.addItem(QListWidgetItem(a))

    def _validate_and_accept(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing project name", "Please enter a project name.")
            return
        self.accept()

    def build_project(self) -> ProjectItem:
        pid = self._project.id if self._project else str(uuid.uuid4())
        title = self.title_edit.text().strip()
        status = TaskStatus(self.status_combo.currentText())
        category = self.category_combo.currentText().strip() or 'Coding'
        code_path = self.code_path_edit.text().strip()
        links = [l.strip() for l in self.links_edit.toPlainText().splitlines() if l.strip()]
        details_html = self.details_edit.toHtml()
        attachments = []
        for i in range(self.attach_list.count()):
            attachments.append(self.attach_list.item(i).text())

        now = datetime.now()
        updated = now
        finished_dt = self._project.finished_dt if self._project else None

        reminder_dt = self.rem_time_edit.dateTime().toPyDateTime() if self.rem_time_enable.isChecked() else None

        p = ProjectItem(
            id=pid,
            title=title,
            status=status,
            category=category,
            code_path=code_path,
            links=links,
            details_html=details_html,
            reminder_dt=reminder_dt,
            updated_dt=updated,
            finished_dt=finished_dt,
            attachments=attachments,
            order=getattr(self._project, "order", 0) if self._project else 0,
            remind_at=bool(self.rem_at.isChecked()),
            remind_10m=bool(self.rem_10m.isChecked()),
            remind_1h=bool(self.rem_1h.isChecked()),
            sent_at=getattr(self._project, "sent_at", False) if self._project else False,
            sent_10m=getattr(self._project, "sent_10m", False) if self._project else False,
            sent_1h=getattr(self._project, "sent_1h", False) if self._project else False,
        )

        # If timing changed, reset sent flags.
        if self._project:
            if getattr(self._project, "reminder_dt", None) != reminder_dt:
                p.reset_reminder_sent_flags()

        p.mark_status(status, now=now)
        return p
