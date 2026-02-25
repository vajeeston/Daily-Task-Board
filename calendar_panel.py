"""
Calendar panel: select a date and see tasks on that date.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCalendarWidget,
    QListWidget, QListWidgetItem, QTableView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QEvent, QObject, QMimeData
from PyQt5.QtGui import QTextCharFormat, QColor, QBrush, QDrag

from icon_utils import load_icon

from models import DailyTask, TaskStatus

# Pastel status colors (must match the NoticeBoard for a consistent UI)
STATUS_COLORS = {
    TaskStatus.UNFINISHED: QColor("#ffe4e6"),  # light red
    TaskStatus.WORKING: QColor("#dbeafe"),     # light blue
    TaskStatus.POSTPONED: QColor("#fef3c7"),   # light amber
    TaskStatus.FINISHED: QColor("#dcfce7"),    # light green
}



class CalendarPanel(QWidget):
    add_task_for_date = pyqtSignal(object)  # datetime default
    edit_task_requested = pyqtSignal(str)
    task_move_requested = pyqtSignal(str, object)  # task_id, new_date (datetime.date)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: List[DailyTask] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        header = QHBoxLayout()
        title = QLabel("Calendar")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()

        self.today_btn = QPushButton("Today")
        self.today_btn.setIcon(load_icon("ic_today.png"))
        self.add_btn = QPushButton("Add Task")
        self.add_btn.setIcon(load_icon("ic_add.png"))
        self.today_btn.setObjectName("SecondaryButton")
        self.add_btn.setObjectName("PrimaryButton")
        header.addWidget(self.today_btn)
        header.addWidget(self.add_btn)
        layout.addLayout(header)

        self.cal = QCalendarWidget()
        self.cal.setObjectName("MainCalendar")
        self.cal.setGridVisible(True)
        layout.addWidget(self.cal)

        self.tasks_label = QLabel("Tasks on selected date:")
        self.tasks_label.setObjectName("TasksSelectedLabel")
        layout.addWidget(self.tasks_label)
        self.list = _DragTaskListWidget()
        self.list.setMinimumHeight(180)
        layout.addWidget(self.list)

        self.setLayout(layout)

        self.today_btn.clicked.connect(lambda: self.cal.setSelectedDate(QDate.currentDate()))
        self.add_btn.clicked.connect(self._add_task_clicked)
        self.cal.selectionChanged.connect(self._refresh_list)
        self.list.itemDoubleClicked.connect(self._edit_from_item)

        # Drag & drop scheduling: drag a task from the list onto a day in the calendar.
        self._install_calendar_drop()

    def _install_calendar_drop(self):
        view = self.cal.findChild(QTableView)
        if view is None:
            return
        view.setAcceptDrops(True)
        view.setDragDropMode(QAbstractItemView.DropOnly)
        self._drop_filter = _CalendarDropFilter(self.cal)
        self._drop_filter.task_dropped.connect(self.task_move_requested)
        view.viewport().installEventFilter(self._drop_filter)

    def set_tasks(self, tasks: List[DailyTask]):
        self._tasks = list(tasks)
        self._highlight()
        self._refresh_list()

    def _selected_date(self) -> date:
        qd = self.cal.selectedDate()
        return date(qd.year(), qd.month(), qd.day())

    def _add_task_clicked(self):
        d = self._selected_date()
        default_dt = datetime(d.year, d.month, d.day, datetime.now().hour, datetime.now().minute)
        self.add_task_for_date.emit(default_dt)

    def _edit_from_item(self, item: QListWidgetItem):
        tid = item.data(Qt.UserRole)
        if tid:
            self.edit_task_requested.emit(str(tid))

    def _refresh_list(self):
        d = self._selected_date()
        self.list.clear()
        tasks_on_day = [t for t in self._tasks if t.start_dt.date() == d and not t.is_note]
        notes_on_day = [t for t in self._tasks if t.start_dt.date() == d and t.is_note]

        for t in sorted(tasks_on_day, key=lambda x: x.start_dt):
            txt = f"{t.start_dt.strftime('%H:%M')}  {t.title}  [{t.status.value}]"
            it = QListWidgetItem(txt)
            it.setData(Qt.UserRole, t.id)
            # Color by status for quick scanning
            it.setBackground(QBrush(STATUS_COLORS.get(t.status, QColor(255, 255, 255, 0))))
            self.list.addItem(it)

        for n in sorted(notes_on_day, key=lambda x: x.start_dt):
            txt = f"📝 {n.title}"
            it = QListWidgetItem(txt)
            it.setData(Qt.UserRole, n.id)
            it.setForeground(Qt.darkGray)
            it.setBackground(QBrush(QColor("#f3f4f6")))
            self.list.addItem(it)

    def _highlight(self):
        # clear
        self.cal.setDateTextFormat(QDate(), QTextCharFormat())

        by_date = {}
        for t in self._tasks:
            by_date.setdefault(t.start_dt.date(), []).append(t)

        for d, items in by_date.items():
            qd = QDate(d.year, d.month, d.day)
            fmt = QTextCharFormat()
            # Color logic (priority): unfinished > working > postponed > finished
            if any(t.status == TaskStatus.UNFINISHED for t in items):
                fmt.setBackground(QBrush(QColor(244, 63, 94, 50)))  # red tint
            elif any(t.status == TaskStatus.WORKING for t in items):
                fmt.setBackground(QBrush(QColor(59, 130, 246, 50)))  # blue tint
            elif any(t.status == TaskStatus.POSTPONED for t in items):
                fmt.setBackground(QBrush(QColor(245, 158, 11, 50)))  # amber tint
            elif any(t.status == TaskStatus.FINISHED for t in items):
                fmt.setBackground(QBrush(QColor(34, 197, 94, 45)))  # green tint
            else:
                fmt.setBackground(QBrush(QColor(229, 231, 235, 40)))
            self.cal.setDateTextFormat(qd, fmt)


class _DragTaskListWidget(QListWidget):
    """A list widget that drags the selected task id as MIME data."""

    MIME = "application/x-daily-task-id"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
        tid = item.data(Qt.UserRole)
        if not tid:
            return
        md = QMimeData()
        md.setData(self.MIME, str(tid).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(md)
        drag.exec_(Qt.MoveAction)


class _CalendarDropFilter(QObject):
    """Accept drops on the calendar month grid."""

    task_dropped = pyqtSignal(str, object)  # task_id, date

    def __init__(self, cal: QCalendarWidget):
        super().__init__(cal)
        self._cal = cal

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.DragEnter, QEvent.DragMove):
            if event.mimeData().hasFormat(_DragTaskListWidget.MIME):
                event.acceptProposedAction()
                return True
            return False

        if event.type() == QEvent.Drop:
            md = event.mimeData()
            if not md.hasFormat(_DragTaskListWidget.MIME):
                return False
            try:
                tid = bytes(md.data(_DragTaskListWidget.MIME)).decode("utf-8")
            except Exception:
                return False

            # Map drop position to a date.
            d = None
            try:
                view = self._cal.findChild(QTableView)
                if view is not None:
                    idx = view.indexAt(event.pos())
                    qd = view.model().data(idx, Qt.UserRole)
                    if isinstance(qd, QDate) and qd.isValid():
                        d = qd.toPyDate()
            except Exception:
                d = None

            if d is None:
                d = self._cal.selectedDate().toPyDate()

            self.task_dropped.emit(str(tid), d)
            event.acceptProposedAction()
            return True

        return False
