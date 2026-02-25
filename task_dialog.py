"""Task dialog.

Includes:
- Title
- Start datetime
- Optional due datetime
- Status (Unfinished/Working/Postponed/Finished)
- Reminders (at time / 10 min before / 1 hour before)
- Details (rich text) + insert image
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional, List
import uuid
import re

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QDateTimeEdit, QFileDialog, QCheckBox, QLabel, QListWidget,
    QListWidgetItem, QMessageBox
)
from PyQt5.QtCore import Qt, QDateTime

from icon_utils import load_icon

from models import DailyTask, TaskStatus


_IMG_SRC_RE = re.compile(r'src="([^"]+)"')


def _normalize_src(src: str) -> str:
    # QTextEdit sometimes stores file urls
    if src.startswith("file:///"):
        return src.replace("file:///", "/")
    if src.startswith("file://"):
        return src.replace("file://", "")
    return src


class TaskDialog(QDialog):
    def __init__(self, parent=None, task: Optional[DailyTask] = None, default_start: Optional[datetime] = None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Task Details" if task else "New Task")
        self.resize(720, 520)

        self._task = task
        self._default_start = default_start or datetime.now()

        self._init_ui()

        if task:
            self._load(task)
        else:
            self.start_dt_edit.setDateTime(QDateTime(self._default_start))

    def _init_ui(self):
        root = QVBoxLayout()

        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Short name (e.g. 'Gym', 'Read 20 pages')")
        form.addRow("Task:", self.title_edit)

        self.start_dt_edit = QDateTimeEdit()
        self.start_dt_edit.setCalendarPopup(True)
        self.start_dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_dt_edit.setDateTime(QDateTime.currentDateTime())
        form.addRow("Start:", self.start_dt_edit)

        # Optional due time
        due_row = QHBoxLayout()
        self.due_enable = QCheckBox("Enable")
        self.due_dt_edit = QDateTimeEdit()
        self.due_dt_edit.setCalendarPopup(True)
        self.due_dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.due_dt_edit.setDateTime(QDateTime.currentDateTime())
        self.due_dt_edit.setEnabled(False)
        due_row.addWidget(self.due_enable)
        due_row.addWidget(self.due_dt_edit, 1)
        form.addRow("Due:", due_row)

        self.status_combo = QComboBox()
        self.status_combo.setObjectName("StatusCombo")
        self.status_combo.addItems([s.value for s in TaskStatus])
        self.status_combo.setProperty("taskStatus", self.status_combo.currentText())
        self.status_combo.currentTextChanged.connect(self._sync_status_style)
        form.addRow("Status:", self.status_combo)

        self.is_note_check = QCheckBox("This is a note (shows in Today tab only)")
        form.addRow("", self.is_note_check)

        # Reminders
        rem_row = QHBoxLayout()
        self.rem_at = QCheckBox("At time")
        self.rem_10m = QCheckBox("10 min before")
        self.rem_1h = QCheckBox("1 hour before")
        rem_row.addWidget(self.rem_at)
        rem_row.addWidget(self.rem_10m)
        rem_row.addWidget(self.rem_1h)
        rem_row.addStretch()
        form.addRow("Reminders:", rem_row)

        root.addLayout(form)

        # Details editor
        root.addWidget(QLabel("Details (text, checklists, images):"))
        self.details_edit = QTextEdit()
        self.details_edit.setAcceptRichText(True)
        root.addWidget(self.details_edit, stretch=1)

        # Attachments list
        attach_row = QHBoxLayout()
        attach_row.addWidget(QLabel("Attachments:"))
        self.attach_list = QListWidget()
        self.attach_list.setMaximumHeight(80)
        attach_row.addWidget(self.attach_list, stretch=1)

        attach_btns = QVBoxLayout()
        self.add_attach_btn = QPushButton("Add File")
        self.remove_attach_btn = QPushButton("Remove")
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
        self.clear_details_btn = QPushButton("Clear Details")
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

        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._validate_and_accept)
        self.insert_image_btn.clicked.connect(self._insert_image)
        self.clear_details_btn.clicked.connect(self.details_edit.clear)
        self.add_attach_btn.clicked.connect(self._add_attachment)
        self.remove_attach_btn.clicked.connect(self._remove_attachment)

        self.due_enable.toggled.connect(self._toggle_due)
        self.is_note_check.toggled.connect(self._toggle_note_mode)

    def _toggle_due(self, checked: bool):
        self.due_dt_edit.setEnabled(bool(checked))

    def _toggle_note_mode(self, is_note: bool):
        # Notes shouldn't fire reminders.
        enable = not bool(is_note)
        for cb in (self.rem_at, self.rem_10m, self.rem_1h):
            cb.setEnabled(enable)
            if not enable:
                cb.setChecked(False)


    def _sync_status_style(self):
        """Update dynamic property so QSS can recolor the status combo."""
        if not hasattr(self, "status_combo"):
            return
        txt = self.status_combo.currentText()
        self.status_combo.setProperty("taskStatus", txt)
        self.status_combo.style().unpolish(self.status_combo)
        self.status_combo.style().polish(self.status_combo)
        self.status_combo.update()

    def _load(self, task: DailyTask):
        self.title_edit.setText(task.title)
        self.start_dt_edit.setDateTime(QDateTime(task.start_dt))
        if getattr(task, "due_dt", None):
            self.due_enable.setChecked(True)
            self.due_dt_edit.setEnabled(True)
            self.due_dt_edit.setDateTime(QDateTime(task.due_dt))
        else:
            self.due_enable.setChecked(False)
            self.due_dt_edit.setEnabled(False)
        self.status_combo.setCurrentText(task.status.value)
        self._sync_status_style()
        self.details_edit.setHtml(task.details_html or "")
        self.is_note_check.setChecked(bool(task.is_note))
        self._toggle_note_mode(bool(task.is_note))

        # Reminders
        self.rem_at.setChecked(bool(getattr(task, "remind_at", False)))
        self.rem_10m.setChecked(bool(getattr(task, "remind_10m", False)))
        self.rem_1h.setChecked(bool(getattr(task, "remind_1h", False)))
        self.attach_list.clear()
        for a in task.attachments:
            self.attach_list.addItem(QListWidgetItem(a))

    def _validate_and_accept(self):
        title = self.title_edit.text().strip()
        if not title and not self.is_note_check.isChecked():
            QMessageBox.warning(self, "Missing title", "Please enter a short task name.")
            return
        self.accept()

    def _insert_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Insert Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if not filename:
            return
        # Insert into QTextEdit at cursor
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

    def build_task(self) -> DailyTask:
        """Create a DailyTask from dialog fields. If editing, preserves id."""
        task_id = self._task.id if self._task else str(uuid.uuid4())
        title = self.title_edit.text().strip() or "(Note)"
        start_dt = self.start_dt_edit.dateTime().toPyDateTime()
        due_dt = self.due_dt_edit.dateTime().toPyDateTime() if self.due_enable.isChecked() else None
        status = TaskStatus(self.status_combo.currentText())
        details_html = self.details_edit.toHtml()
        is_note = bool(self.is_note_check.isChecked())
        attachments = []
        for i in range(self.attach_list.count()):
            attachments.append(self.attach_list.item(i).text())

        t = DailyTask(
            id=task_id,
            title=title,
            start_dt=start_dt,
            due_dt=due_dt,
            status=status,
            details_html=details_html,
            is_note=is_note,
            attachments=attachments,
            finished_dt=self._task.finished_dt if self._task else None,
            order=getattr(self._task, "order", 0) if self._task else 0,
            remind_at=bool(self.rem_at.isChecked()),
            remind_10m=bool(self.rem_10m.isChecked()),
            remind_1h=bool(self.rem_1h.isChecked()),
            sent_at=getattr(self._task, "sent_at", False) if self._task else False,
            sent_10m=getattr(self._task, "sent_10m", False) if self._task else False,
            sent_1h=getattr(self._task, "sent_1h", False) if self._task else False,
        )

        # If timing changed, reset sent flags.
        if self._task:
            old_base = getattr(self._task, "due_dt", None) or self._task.start_dt
            new_base = due_dt or start_dt
            if old_base != new_base:
                t.reset_reminder_sent_flags()

        # Ensure finished_dt logic
        t.mark_status(status)
        return t
