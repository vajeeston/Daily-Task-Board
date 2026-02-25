"""
Notice board widget:
Tabs:
- Today's tasks/notes
- Pending
- Finished
"""
from __future__ import annotations

import re

from datetime import date
from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QHeaderView, QComboBox, QStyle,
    QFrame, QSizePolicy, QAbstractItemView, QProgressBar, QGridLayout, QMenu, QMessageBox, QApplication, QToolButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QElapsedTimer, QUrl
from PyQt5.QtGui import QColor, QDesktopServices, QCursor,  QFont

from icon_utils import load_icon

from models import DailyTask, TaskStatus, ProjectItem

# Pastel status colors used across the task tables (better scanability)
STATUS_COLORS = {
    TaskStatus.UNFINISHED: QColor("#ffe4e6"),  # light red
    TaskStatus.WORKING: QColor("#dbeafe"),     # light blue
    TaskStatus.POSTPONED: QColor("#fef3c7"),   # light amber
    TaskStatus.FINISHED: QColor("#dcfce7"),    # light green
}
NOTE_COLOR = QColor("#f3f4f6")  # neutral gray for notes


# Project categories for the Projects tab
PROJECT_CATEGORIES = ["Study", "Research", "Lab", "Coding", "Personal"]
CATEGORY_COLORS = {
    "Study": QColor("#E6FFFA"),     # teal-tint
    "Research": QColor("#F3E8FF"),  # violet-tint
    "Lab": QColor("#FFF7ED"),       # orange-tint
    "Coding": QColor("#ECFDF5"),    # green-tint
    "Personal": QColor("#FFF1F2"),  # pink-tint
}


class _ReorderableTable(QTableWidget):
    """QTableWidget that emits when an internal row move is dropped."""

    rows_dropped = pyqtSignal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.rows_dropped.emit()


class DigitalClock(QWidget):
    """Modern digital clock pill (date + time) with no overlap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DigitalClock")
        # Ensure the stylesheet background is actually painted on a QWidget subclass
        # (Qt sometimes needs WA_StyledBackground for custom widgets).
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Match the requested look: date (top) + big time (bottom).
        self.setMinimumWidth(190)
        self.setFixedHeight(60)

        self.setStyleSheet(
            """
            #DigitalClock {
                background-color: #0b4f63;   /* teal/blue like the reference */
                border: 1px solid #063242;
                border-radius: 12px;
            }
            #ClockDate {
                color: rgba(255,255,255,230);
                font-size: 12px;
                font-weight: 700;
            }
            #ClockTime {
                color: #ffb000;              /* warm orange digits */
                font-size: 22px;
                font-weight: 900;
            }
            """
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(0)

        self.date_label = QLabel(self)
        self.date_label.setObjectName("ClockDate")
        self.date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.time_label = QLabel(self)
        self.time_label.setObjectName("ClockTime")
        self.time_label.setAlignment(Qt.AlignCenter)

        lay.addWidget(self.date_label, 0)
        lay.addStretch(1)
        lay.addWidget(self.time_label, 0)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def _tick(self):
        from datetime import datetime

        now = datetime.now()
        self.date_label.setText(now.strftime("%d-%m-%Y"))
        self.time_label.setText(now.strftime("%H:%M:%S"))


class StopWatchWidget(QWidget):
    """Stopwatch pill styled like the reference (click to start/pause, right-click for menu)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StopwatchWidget")
        # Ensure the stylesheet background is actually painted on a QWidget subclass.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumWidth(190)
        self.setFixedHeight(60)

        self.setStyleSheet(
            """
            #StopwatchWidget {
                background-color: #1f6b2a;  /* deep green like the reference */
                border: 1px solid #14461c;
                border-radius: 12px;
            }
            #StopwatchTitle {
                color: rgba(255,255,255,235);
                font-size: 12px;
                font-weight: 800;
            }
            #StopwatchTime {
                color: #ffb000;
                font-size: 22px;
                font-weight: 900;
            }
            """
        )

        self._running = False
        self._elapsed_timer = QElapsedTimer()
        self._accumulated_ms = 0

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._refresh)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(0)

        self.title_label = QLabel("Stop clock", self)
        self.title_label.setObjectName("StopwatchTitle")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.time_label = QLabel("00:00:00", self)
        self.time_label.setObjectName("StopwatchTime")
        self.time_label.setAlignment(Qt.AlignCenter)

        lay.addWidget(self.title_label, 0)
        lay.addStretch(1)
        lay.addWidget(self.time_label, 0)

        self.setToolTip("Left click: Start/Pause\nRight click: Reset")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
            event.accept()
            return
        if event.button() == Qt.RightButton:
            self._show_menu(event.globalPos())
            event.accept()
            return
        super().mousePressEvent(event)

    def _show_menu(self, pos):
        m = QMenu(self)
        act_toggle = m.addAction("Pause" if self._running else "Start")
        act_reset = m.addAction("Reset")
        chosen = m.exec_(pos)
        if chosen == act_toggle:
            self.toggle()
        elif chosen == act_reset:
            self.reset()

    def toggle(self):
        if self._running:
            self._accumulated_ms += int(self._elapsed_timer.elapsed())
            self._running = False
            self._timer.stop()
            self._refresh()
        else:
            self._elapsed_timer.restart()
            self._running = True
            self._timer.start()
            self._refresh()

    def reset(self):
        self._running = False
        self._timer.stop()
        self._accumulated_ms = 0
        self._refresh()

    def _refresh(self):
        ms = self._accumulated_ms
        if self._running:
            ms += int(self._elapsed_timer.elapsed())
        total_seconds = ms // 1000
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        self.time_label.setText(f"{h:02d}:{m:02d}:{s:02d}")
        return



class DashboardWidget(QWidget):
    """Lightweight analytics dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        root.addLayout(grid)

        self.lbl_done_today = QLabel("0")
        self.lbl_done_week = QLabel("0")
        self.lbl_streak = QLabel("0 days")
        self.lbl_active_projects = QLabel("0")

        def card(label: str, value_lbl: QLabel) -> QWidget:
            box = QFrame()
            box.setObjectName("DashCard")
            box.setFrameShape(QFrame.StyledPanel)
            v = QVBoxLayout(box)
            v.setContentsMargins(12, 10, 12, 10)
            l1 = QLabel(label)
            l1.setStyleSheet("color: #374151;")
            value_lbl.setStyleSheet("font-size: 18px; font-weight: 800;")
            v.addWidget(l1)
            v.addWidget(value_lbl)
            return box

        grid.addWidget(card("Tasks completed today", self.lbl_done_today), 0, 0)
        grid.addWidget(card("Tasks completed this week", self.lbl_done_week), 0, 1)
        grid.addWidget(card("Completion streak", self.lbl_streak), 1, 0)
        grid.addWidget(card("Projects active this month", self.lbl_active_projects), 1, 1)

        # Distribution
        dist_box = QFrame()
        dist_box.setFrameShape(QFrame.StyledPanel)
        dist_box.setObjectName("DashCard")
        dv = QVBoxLayout(dist_box)
        dv.setContentsMargins(12, 10, 12, 10)
        dv.addWidget(QLabel("Status distribution (active tasks)"))
        self.pb_unfinished = QProgressBar(); self.pb_unfinished.setFormat("Unfinished: %p%")
        self.pb_working = QProgressBar(); self.pb_working.setFormat("Working: %p%")
        self.pb_postponed = QProgressBar(); self.pb_postponed.setFormat("Postponed: %p%")
        self.pb_finished = QProgressBar(); self.pb_finished.setFormat("Finished: %p%")
        for pb in (self.pb_unfinished, self.pb_working, self.pb_postponed, self.pb_finished):
            pb.setMaximum(100)
            pb.setTextVisible(True)
            dv.addWidget(pb)
        root.addWidget(dist_box)
        root.addStretch(1)

    def set_data(self, tasks: List[DailyTask], projects: List[ProjectItem]):
        today = date.today()

        done_today = [t for t in tasks if (not t.is_note) and t.status == TaskStatus.FINISHED and t.finished_dt and t.finished_dt.date() == today]
        self.lbl_done_today.setText(str(len(done_today)))

        # last 7 days inclusive
        from_dt = today.toordinal() - 6
        done_week = [t for t in tasks if (not t.is_note) and t.status == TaskStatus.FINISHED and t.finished_dt and t.finished_dt.date().toordinal() >= from_dt]
        self.lbl_done_week.setText(str(len(done_week)))

        # streak: consecutive days with >= 1 completion
        finished_dates = sorted({t.finished_dt.date() for t in tasks if (not t.is_note) and t.finished_dt}, reverse=True)
        streak = 0
        cur = today
        sset = set(finished_dates)
        while cur in sset:
            streak += 1
            cur = date.fromordinal(cur.toordinal() - 1)
        self.lbl_streak.setText(f"{streak} days")

        # active projects this month
        active_projects = [p for p in projects if p.status != TaskStatus.FINISHED and p.updated_dt and (p.updated_dt.year == today.year and p.updated_dt.month == today.month)]
        self.lbl_active_projects.setText(str(len(active_projects)))

        # distribution among non-note tasks
        active_tasks = [t for t in tasks if not t.is_note]
        total = max(1, len(active_tasks))
        def pct(n: int) -> int:
            return int(round((n / total) * 100))

        n_unf = sum(1 for t in active_tasks if t.status == TaskStatus.UNFINISHED)
        n_w = sum(1 for t in active_tasks if t.status == TaskStatus.WORKING)
        n_p = sum(1 for t in active_tasks if t.status == TaskStatus.POSTPONED)
        n_f = sum(1 for t in active_tasks if t.status == TaskStatus.FINISHED)
        self.pb_unfinished.setValue(pct(n_unf))
        self.pb_working.setValue(pct(n_w))
        self.pb_postponed.setValue(pct(n_p))
        self.pb_finished.setValue(pct(n_f))


class TaskTable(QWidget):
    task_edit_requested = pyqtSignal(str)
    task_delete_requested = pyqtSignal(str)
    task_add_requested = pyqtSignal(object)  # default_start datetime
    task_status_changed = pyqtSignal(str, str)  # id, new_status
    task_order_changed = pyqtSignal(list)  # list of task ids in visual order

    def __init__(self, title: str, parent=None, allow_reorder: bool = False):
        super().__init__(parent)
        self._title = title
        self._tasks: List[DailyTask] = []
        self._allow_reorder = bool(allow_reorder)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        header = QHBoxLayout()
        label = QLabel(self._title)
        label.setStyleSheet("font-size: 16px; font-weight: 700;")
        header.addWidget(label)
        header.addStretch()

        self.add_btn = QPushButton("Add")
        self.add_btn.setIcon(load_icon("ic_add.png"))
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setIcon(load_icon("ic_edit.png"))
        self.del_btn = QPushButton("Delete")
        self.del_btn.setIcon(load_icon("ic_delete.png"))
        # styling hooks (see global stylesheet)
        self.add_btn.setObjectName("PrimaryButton")
        self.edit_btn.setObjectName("SecondaryButton")
        self.del_btn.setObjectName("DangerButton")
        header.addWidget(self.add_btn)
        header.addWidget(self.edit_btn)
        header.addWidget(self.del_btn)
        layout.addLayout(header)

        self.table = _ReorderableTable() if self._allow_reorder else QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Task", "Status", "Start", "Finished"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        if self._allow_reorder and isinstance(self.table, _ReorderableTable):
            self.table.setDragEnabled(True)
            self.table.setAcceptDrops(True)
            self.table.setDropIndicatorShown(True)
            self.table.setDragDropMode(QAbstractItemView.InternalMove)
            self.table.rows_dropped.connect(self._on_rows_dropped)

        # Better viewability
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(False)

        layout.addWidget(self.table)

        details_lbl = QLabel("Details preview:")
        details_lbl.setObjectName("DetailsPreviewLabel")
        layout.addWidget(details_lbl)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(180)
        self.preview.setObjectName("DetailsPreview")
        layout.addWidget(self.preview)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self._add_clicked)
        self.edit_btn.clicked.connect(self._edit_clicked)
        self.del_btn.clicked.connect(self._del_clicked)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.cellDoubleClicked.connect(lambda r, c: self._edit_clicked())

    def set_tasks(self, tasks: List[DailyTask]):
        self._tasks = list(tasks)
        self._render()

    def _on_status_combo_changed(self, task_id: str, combo: QComboBox, text: str):
        # Update dynamic property so theme QSS can recolor the combo immediately
        combo.setProperty("taskStatus", text)
        combo.style().unpolish(combo)
        combo.style().polish(combo)
        combo.update()
        self.task_status_changed.emit(task_id, text)

    def _render(self):
        self.table.setRowCount(0)
        def _key(x: DailyTask):
            o = int(getattr(x, "order", 0) or 0)
            if o > 0:
                return (0, o)
            return (1, x.start_dt)

        for t in sorted(self._tasks, key=_key):
            row = self.table.rowCount()
            self.table.insertRow(row)

            item = QTableWidgetItem(t.title)
            item.setData(Qt.UserRole, t.id)
            if t.is_note:
                item.setForeground(Qt.darkGray)
                item.setText(f"📝 {t.title}")
            self.table.setItem(row, 0, item)

            # Row coloring by status (quick visual scan)
            row_color = NOTE_COLOR if t.is_note else STATUS_COLORS.get(t.status, QColor("#ffffff"))

            # Status combo (cell widget)
            status_combo = QComboBox()
            status_combo.setObjectName("StatusCombo")
            status_combo.setProperty("taskStatus", t.status.value)
            status_combo.addItems([s.value for s in TaskStatus])
            status_combo.setCurrentText(t.status.value)
            status_combo.currentTextChanged.connect(
                lambda txt, tid=t.id, cmb=status_combo: self._on_status_combo_changed(tid, cmb, txt)
            )

            # Wrap combo in a background widget so the whole cell is colored
            cell = QWidget()
            cell.setObjectName("StatusCell")
            cell.setProperty("rowStatus", t.status.value)
            cell.setStyleSheet(f"background: {row_color.name()}; border: none;")
            hl = QHBoxLayout(cell)
            hl.setContentsMargins(6, 2, 6, 2)
            hl.addWidget(status_combo)
            # Column order is: 0=Task, 1=Status, 2=Start, 3=Finished
            # (A previous refactor accidentally placed the Status widget into column 2,
            # which shifted all visual columns. Keep Status strictly in column 1.)
            self.table.setCellWidget(row, 1, cell)

            self.table.setItem(row, 2, QTableWidgetItem(t.start_dt.strftime("%Y-%m-%d %H:%M")))
            self.table.setItem(row, 3, QTableWidgetItem(t.finished_dt.strftime("%Y-%m-%d %H:%M") if t.finished_dt else ""))

            # Color the other cells
            for col in (0, 2, 3):
                it = self.table.item(row, col)
                if it:
                    it.setBackground(row_color)

            # Notes are slightly muted
            if t.is_note:
                for col in (0, 2, 3):
                    it = self.table.item(row, col)
                    if it:
                        it.setForeground(Qt.darkGray)
                        f = it.font()
                        f.setItalic(True)
                        it.setFont(f)

        self.preview.clear()

    def _on_rows_dropped(self):
        """Handle drag-reordering (Today tab)."""
        ids: List[str] = []
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it is not None:
                tid = it.data(Qt.UserRole)
                if tid:
                    ids.append(str(tid))

        if not ids:
            return

        # Reorder internal list to match the visual order.
        id_to_task = {t.id: t for t in self._tasks}
        new_list = [id_to_task[i] for i in ids if i in id_to_task]
        self._tasks = new_list

        # Persist manual order (best effort)
        for idx, t in enumerate(self._tasks, start=1):
            try:
                t.order = idx
            except Exception:
                pass

        self.task_order_changed.emit(ids)
        self._render()

    def _selected_task_id(self) -> Optional[str]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        r = rows[0].row()
        item = self.table.item(r, 0)
        if not item:
            return None
        return item.data(Qt.UserRole)

    
    def _build_preview_html(self, raw_html: str) -> str:
        """Render details preview using a split template:

        - If images exist: left "Notes and text" box + right "Image thumbnails" box.
        - If no images: a full-width "Notes and text" box.

        Implemented using Qt-rich-text-friendly HTML (mostly inline styles).
        """
        raw_html = raw_html or ""
        if not raw_html.strip():
            raw_html = "<p><i>No details.</i></p>"

        # Collect <img ...> tags
        img_tags = re.findall(r"<img\b[^>]*>", raw_html, flags=re.IGNORECASE)
        if not img_tags:
            # Full-width text mode (no image panel)
            text_html = raw_html.strip()
            return f"""
            <div style="border:1px solid #111827; padding:12px;">
              <div style="font-size:14px; font-weight:600; margin-bottom:8px;">Notes and text:</div>
              <div style="border:2px dotted #3b82f6; padding:12px; min-height:220px;">{text_html}</div>
            </div>
            """

        # Remove images from main text so the preview stays compact
        text_html = re.sub(r"<img\b[^>]*>", "", raw_html, flags=re.IGNORECASE).strip()

        # If text becomes empty (only images), keep a small placeholder cell
        text_plain = re.sub(r"<[^>]+>", "", text_html).strip()
        if not text_plain:
            text_html = "<p><i></i></p>"

        # --- Thumbnails ---
        # Qt5 rich-text does NOT reliably honor CSS max-width/max-height for <img> tags.
        # The most reliable approach is to rebuild the <img> tag and set a fixed width attribute.
        THUMB_W = 260  # px (keeps images visually compact in the preview)
        thumb_style = (
            "border:1px solid rgba(17,24,39,0.65);"
            "padding:2px;"
            "margin:8px 0;"
        )

        def make_thumb(tag: str) -> str:
            # Extract src from the original tag and rebuild a clean thumbnail tag.
            m = re.search(r"\bsrc\s*=\s*([\"\'])(.*?)\1", tag, flags=re.IGNORECASE | re.DOTALL)
            src = m.group(2).strip() if m else ""
            # Use width attribute (Qt honors it) and omit height (keeps aspect ratio).
            if src:
                return f'<img src="{src}" width="{THUMB_W}" style="{thumb_style}">' 

            # Fallback: keep the tag but force width if src was not found.
            # Remove existing width/height attrs if present.
            cleaned = re.sub(r"\b(width|height)\s*=\s*([\"\']).*?\2", "", tag, flags=re.IGNORECASE)
            if cleaned.endswith(">"):
                cleaned = cleaned[:-1] + f' width="{THUMB_W}" style="{thumb_style}">' 
            return cleaned

        thumbs = []
        for tag in img_tags:
            thumbs.append(f'<div style="text-align:center;">{make_thumb(tag)}</div>')
        thumbs_html = "".join(thumbs)

        # Split template (matches user's mockup):
        # left: notes/text in a dotted box; right: thumbnails in a framed box.
        return f"""
        <div style="border:1px solid #111827; padding:12px;">
          <table width="100%" cellspacing="0" cellpadding="0">
            <tr>
              <td valign="top" style="width:60%; padding-right:18px;">
                <div style="font-size:14px; font-weight:600; margin-bottom:8px;">Notes and text:</div>
                <div style="border:2px dotted #3b82f6; padding:12px; min-height:220px;">{text_html}</div>
              </td>
              <td valign="top" style="width:40%;">
                <div style="font-size:14px; font-weight:600; margin-bottom:8px;">Image thumbnails:</div>
                <div style="border:2px solid #111827; padding:8px;">{thumbs_html}</div>
              </td>
            </tr>
          </table>
        </div>
        """


    def _selection_changed(self):
        tid = self._selected_task_id()
        if not tid:
            self.preview.clear()
            return
        t = next((x for x in self._tasks if x.id == tid), None)
        if not t:
            self.preview.clear()
            return

        html = self._build_preview_html(t.details_html or "")
        if not html.strip():
            html = "<p><i>No details.</i></p>"
        self.preview.setHtml(html)

    def _add_clicked(self):
        self.task_add_requested.emit(None)

    def _edit_clicked(self):
        tid = self._selected_task_id()
        if tid:
            self.task_edit_requested.emit(tid)

    def _del_clicked(self):
        tid = self._selected_task_id()
        if not tid:
            return
        self.task_delete_requested.emit(tid)




class ProjectTable(QWidget):
    """Projects table + details preview.

    Uses the same status colors as tasks for consistency:
    - Unfinished: planned
    - Working: in progress
    - Postponed: on hold
    - Finished: completed
    """
    project_edit_requested = pyqtSignal(str)
    project_delete_requested = pyqtSignal(str)
    project_add_requested = pyqtSignal(object)  # unused (kept for symmetry)
    project_status_changed = pyqtSignal(str, str)  # id, new_status

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._projects: List[ProjectItem] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        header = QHBoxLayout()
        label = QLabel(self._title)
        label.setStyleSheet("font-size: 16px; font-weight: 700;")
        header.addWidget(label)
        header.addStretch()

        self.add_btn = QPushButton("Add")
        self.add_btn.setIcon(load_icon("ic_add.png"))
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setIcon(load_icon("ic_edit.png"))
        self.del_btn = QPushButton("Delete")
        self.del_btn.setIcon(load_icon("ic_delete.png"))
        header.addWidget(self.add_btn)
        header.addWidget(self.edit_btn)
        header.addWidget(self.del_btn)

        # Quick actions (open code / open link / copy path)
        self.open_code_btn = QPushButton("Open Code")
        self.open_code_btn.setIcon(load_icon("ic_open_folder.png"))
        self.open_link_btn = QPushButton("Open Link")
        self.open_link_btn.setIcon(load_icon("ic_open_link.png"))
        self.copy_path_btn = QPushButton("Copy Path")
        self.copy_path_btn.setIcon(load_icon("ic_copy.png"))
        self.open_code_btn.setObjectName("SecondaryButton")
        self.open_link_btn.setObjectName("SecondaryButton")
        self.copy_path_btn.setObjectName("SecondaryButton")
        header.addSpacing(10)
        header.addWidget(self.open_code_btn)
        header.addWidget(self.open_link_btn)
        header.addWidget(self.copy_path_btn)
        layout.addLayout(header)

        self.table = QTableWidget()
        # Category filter bar
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.addWidget(QLabel("Category filter:"))
        self.category_filter = QComboBox()
        self.category_filter.addItems(["All"] + PROJECT_CATEGORIES)
        self.category_filter.setMinimumWidth(140)
        self.category_filter.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.category_filter)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Project", "Category", "Status", "Updated", "Finished", "Code location"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(False)

        layout.addWidget(self.table)

        layout.addWidget(QLabel("Details preview:"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(220)
        layout.addWidget(self.preview)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self._add_clicked)
        self.edit_btn.clicked.connect(self._edit_clicked)
        self.del_btn.clicked.connect(self._del_clicked)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        # Project quick actions
        self.open_code_btn.clicked.connect(self._open_code)
        self.open_link_btn.clicked.connect(self._open_link)
        self.copy_path_btn.clicked.connect(self._copy_path)
        self.table.cellDoubleClicked.connect(lambda r, c: self._edit_clicked())

    def set_projects(self, projects: List[ProjectItem]):
        self._all_projects = list(projects)
        self._apply_filter()

    def _apply_filter(self):
        cat = self.category_filter.currentText() if hasattr(self, 'category_filter') else 'All'
        if cat == 'All':
            self._projects = list(getattr(self, '_all_projects', []))
        else:
            self._projects = [p for p in getattr(self, '_all_projects', []) if (getattr(p, 'category', 'Coding') or 'Coding') == cat]
        self._render()

    def _selected_project(self) -> Optional[ProjectItem]:
        pid = self._selected_project_id()
        if not pid:
            return None
        return next((x for x in self._projects if x.id == pid), None)

    def _open_code(self):
        p = self._selected_project()
        if not p or not p.code_path:
            QMessageBox.information(self, 'Open code', 'No code location is set for this project.')
            return
        import os
        try:
            path = p.code_path
            if os.path.isdir(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            elif os.path.isfile(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            QMessageBox.warning(self, 'Open code', str(e))

    def _open_link(self):
        p = self._selected_project()
        if not p or not p.links:
            QMessageBox.information(self, 'Open link', 'No links are set for this project.')
            return
        if len(p.links) == 1:
            QDesktopServices.openUrl(QUrl(p.links[0]))
            return
        menu = QMenu(self)
        for u in p.links:
            act = menu.addAction(u)
            act.triggered.connect(lambda checked=False, url=u: QDesktopServices.openUrl(QUrl(url)))
        menu.exec_(QCursor.pos())

    def _copy_path(self):
        p = self._selected_project()
        if not p or not p.code_path:
            QMessageBox.information(self, 'Copy path', 'No code location is set for this project.')
            return
        QApplication.clipboard().setText(p.code_path)
        QMessageBox.information(self, 'Copy path', 'Code location copied to clipboard.')

    def _render(self):
        self.table.setRowCount(0)
        for p in sorted(self._projects, key=lambda x: x.updated_dt, reverse=True):
            row = self.table.rowCount()
            self.table.insertRow(row)

            item = QTableWidgetItem(p.title)
            item.setData(Qt.UserRole, p.id)
            self.table.setItem(row, 0, item)

            row_color = STATUS_COLORS.get(p.status, QColor("#ffffff"))
            # Category pill
            cat = getattr(p, 'category', 'Coding') or 'Coding'
            cat_color = CATEGORY_COLORS.get(cat, QColor('#ECFDF5'))
            cat_cell = QWidget()
            cat_cell.setStyleSheet(f"background: {row_color.name()}; border: none;")
            chl = QHBoxLayout(cat_cell)
            chl.setContentsMargins(6, 2, 6, 2)
            lbl_cat = QLabel(cat)
            lbl_cat.setAlignment(Qt.AlignCenter)
            lbl_cat.setStyleSheet(f"background: {cat_color.name()}; border: 1px solid #d1d5db; border-radius: 10px; padding: 2px 10px; font-weight: 700;")
            chl.addWidget(lbl_cat)
            self.table.setCellWidget(row, 1, cat_cell)

            row_color = STATUS_COLORS.get(p.status, QColor('#ffffff'))

            status_combo = QComboBox()
            status_combo.setObjectName("StatusCombo")
            status_combo.setProperty("taskStatus", p.status.value)
            status_combo.addItems([s.value for s in TaskStatus])
            status_combo.setCurrentText(p.status.value)
            status_combo.currentTextChanged.connect(
                lambda txt, pid=p.id, cmb=status_combo: self._on_status_combo_changed(pid, cmb, txt)
            )

            cell = QWidget()
            cell.setObjectName("StatusCell")
            cell.setProperty("rowStatus", p.status.value)
            cell.setStyleSheet(f"background: {row_color.name()}; border: none;")
            hl = QHBoxLayout(cell)
            hl.setContentsMargins(6, 2, 6, 2)
            hl.addWidget(status_combo)
            self.table.setCellWidget(row, 2, cell)

            self.table.setItem(row, 3, QTableWidgetItem(p.updated_dt.strftime("%Y-%m-%d %H:%M")))
            self.table.setItem(row, 4, QTableWidgetItem(p.finished_dt.strftime("%Y-%m-%d %H:%M") if p.finished_dt else ""))

            code_short = p.code_path or ""
            code_item = QTableWidgetItem(code_short)
            code_item.setToolTip(p.code_path or "")
            self.table.setItem(row, 5, code_item)

            # Color other cells
            for col in (0, 3, 4, 5):
                it = self.table.item(row, col)
                if it:
                    it.setBackground(row_color)

        self.preview.clear()

    def _on_status_combo_changed(self, pid: str, combo: QComboBox, txt: str):
        combo.setProperty("taskStatus", txt)
        combo.style().unpolish(combo)
        combo.style().polish(combo)
        combo.update()
        # Update the background of the wrapper cell and row
        status = TaskStatus(txt)
        row_color = STATUS_COLORS.get(status, QColor("#ffffff"))

        # Find row
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it and it.data(Qt.UserRole) == pid:
                cell = self.table.cellWidget(r, 2)
                if cell:
                    cell.setStyleSheet(f"background: {row_color.name()}; border: none;")
                catw = self.table.cellWidget(r, 1)
                if catw:
                    catw.setStyleSheet(f"background: {row_color.name()}; border: none;")
                for col in (0, 3, 4, 5):
                    item = self.table.item(r, col)
                    if item:
                        item.setBackground(row_color)
                if it:
                    it.setBackground(row_color)
                break

        self.project_status_changed.emit(pid, txt)

    def _selected_project_id(self) -> Optional[str]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        r = rows[0].row()
        item = self.table.item(r, 0)
        if not item:
            return None
        return item.data(Qt.UserRole)



    
    def _build_preview_html(self, raw_html: str) -> str:
        """Render details preview using a split template:

        - If images exist: left "Notes and text" box + right "Image thumbnails" box.
        - If no images: a full-width "Notes and text" box.

        Implemented using Qt-rich-text-friendly HTML (mostly inline styles).
        """
        raw_html = raw_html or ""
        if not raw_html.strip():
            raw_html = "<p><i>No details.</i></p>"

        # Collect <img ...> tags
        img_tags = re.findall(r"<img\b[^>]*>", raw_html, flags=re.IGNORECASE)
        if not img_tags:
            # Full-width text mode (no image panel)
            text_html = raw_html.strip()
            return f"""
            <div style="border:1px solid #111827; padding:12px;">
              <div style="font-size:14px; font-weight:600; margin-bottom:8px;">Notes and text:</div>
              <div style="border:2px dotted #3b82f6; padding:12px; min-height:220px;">{text_html}</div>
            </div>
            """

        # Remove images from main text so the preview stays compact
        text_html = re.sub(r"<img\b[^>]*>", "", raw_html, flags=re.IGNORECASE).strip()

        # If text becomes empty (only images), keep a small placeholder cell
        text_plain = re.sub(r"<[^>]+>", "", text_html).strip()
        if not text_plain:
            text_html = "<p><i></i></p>"

        # --- Thumbnails ---
        # Qt5 rich-text does NOT reliably honor CSS max-width/max-height for <img> tags.
        # The most reliable approach is to rebuild the <img> tag and set a fixed width attribute.
        THUMB_W = 260  # px (keeps images visually compact in the preview)
        thumb_style = (
            "border:1px solid rgba(17,24,39,0.65);"
            "padding:2px;"
            "margin:8px 0;"
        )

        def make_thumb(tag: str) -> str:
            # Extract src from the original tag and rebuild a clean thumbnail tag.
            m = re.search(r"\bsrc\s*=\s*([\"\'])(.*?)\1", tag, flags=re.IGNORECASE | re.DOTALL)
            src = m.group(2).strip() if m else ""
            # Use width attribute (Qt honors it) and omit height (keeps aspect ratio).
            if src:
                return f'<img src="{src}" width="{THUMB_W}" style="{thumb_style}">' 

            # Fallback: keep the tag but force width if src was not found.
            # Remove existing width/height attrs if present.
            cleaned = re.sub(r"\b(width|height)\s*=\s*([\"\']).*?\2", "", tag, flags=re.IGNORECASE)
            if cleaned.endswith(">"):
                cleaned = cleaned[:-1] + f' width="{THUMB_W}" style="{thumb_style}">' 
            return cleaned

        thumbs = []
        for tag in img_tags:
            thumbs.append(f'<div style="text-align:center;">{make_thumb(tag)}</div>')
        thumbs_html = "".join(thumbs)

        # Split template (matches user's mockup):
        # left: notes/text in a dotted box; right: thumbnails in a framed box.
        return f"""
        <div style="border:1px solid #111827; padding:12px;">
          <table width="100%" cellspacing="0" cellpadding="0">
            <tr>
              <td valign="top" style="width:60%; padding-right:18px;">
                <div style="font-size:14px; font-weight:600; margin-bottom:8px;">Notes and text:</div>
                <div style="border:2px dotted #3b82f6; padding:12px; min-height:220px;">{text_html}</div>
              </td>
              <td valign="top" style="width:40%;">
                <div style="font-size:14px; font-weight:600; margin-bottom:8px;">Image thumbnails:</div>
                <div style="border:2px solid #111827; padding:8px;">{thumbs_html}</div>
              </td>
            </tr>
          </table>
        </div>
        """

    def _selection_changed(self):
        pid = self._selected_project_id()
        if not pid:
            self.preview.clear()
            return
        p = next((x for x in self._projects if x.id == pid), None)
        if not p:
            self.preview.clear()
            return

        # Build a compact header section for code + links (shown inside Notes/text panel)
        extra = ""
        if p.code_path:
            esc = p.code_path.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            extra += f"<p><b>Code location:</b> <code>{esc}</code></p>"
        if p.links:
            links_html = "<br>".join([f'<a href="{u}">{u}</a>' for u in p.links])
            extra += f"<p><b>Links:</b><br>{links_html}</p>"

        raw_html = extra + (p.details_html or "")
        self.preview.setHtml(self._build_preview_html(raw_html))

    def _add_clicked(self):
        self.project_add_requested.emit(None)

    def _edit_clicked(self):
        pid = self._selected_project_id()
        if pid:
            self.project_edit_requested.emit(pid)

    def _del_clicked(self):
        pid = self._selected_project_id()
        if not pid:
            return
        self.project_delete_requested.emit(pid)


class NoticeBoard(QWidget):
    task_edit_requested = pyqtSignal(str)
    task_delete_requested = pyqtSignal(str)
    task_add_requested = pyqtSignal(object)  # default start dt
    task_status_changed = pyqtSignal(str, str)
    task_order_changed = pyqtSignal(list)

    project_edit_requested = pyqtSignal(str)
    project_delete_requested = pyqtSignal(str)
    project_add_requested = pyqtSignal(object)
    project_status_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_tasks: List[DailyTask] = []
        self._all_projects: List[ProjectItem] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Top bar: status legend (wide pills) + quick filter + clock
        top_bar = QHBoxLayout()

        legend_frame = QFrame()
        legend_frame.setObjectName("LegendFrame")
        lf = QHBoxLayout(legend_frame)
        lf.setContentsMargins(8, 6, 8, 6)
        lf.setSpacing(10)

        def pill(text: str, status: str):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            lbl.setObjectName("LegendPill")
            lbl.setProperty("status", status)
            lbl.setMinimumHeight(28)
            return lbl

        lf.addWidget(pill("Unfinished", "Unfinished"))
        lf.addWidget(pill("Working", "Working"))
        lf.addWidget(pill("Postponed", "Postponed"))
        lf.addWidget(pill("Finished", "Finished"))

        top_bar.addWidget(legend_frame, 1)

        # Quick filter (applies to Today tab)
        self.quick_filter = QComboBox()
        self.quick_filter.setObjectName("QuickFilter")
        self.quick_filter.addItems([
            "All (Today)",
            "Working only (Today)",
            "Unfinished only (Today)",
            "Postponed only (Today)",
            "Finished only (Today)",
        ])
        self.quick_filter.setMinimumWidth(190)
        self.quick_filter.currentIndexChanged.connect(self._apply_filters)
        top_bar.addWidget(self.quick_filter, 0)

        # Digital clock (oval look via QSS)
        self.clock = DigitalClock()
        top_bar.addWidget(self.clock, 0)

        self.stopwatch = StopWatchWidget()
        top_bar.addWidget(self.stopwatch, 0)

        layout.addLayout(top_bar)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("NoticeTabs")

        self.dashboard_tab = DashboardWidget()

        self.today_tab = TaskTable("Today: tasks + notes", allow_reorder=True)
        self.pending_tab = TaskTable("Pending: unfinished + working + postponed")
        self.finished_tab = TaskTable("Finished")
        self.projects_tab = ProjectTable("Projects: small tools + links + screenshots")

        # Modern tab styling + standard Qt icons (consistent on PyQt5/Windows)
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.setIconSize(QSize(18, 18))

        style = self.style()
        self.tabs.addTab(self.dashboard_tab, load_icon("ic_dashboard.png"), "Dashboard")
        self.tabs.addTab(self.today_tab, load_icon("ic_today.png"), "Today")
        self.tabs.addTab(self.pending_tab, load_icon("ic_pending.png"), "Pending")
        self.tabs.addTab(self.finished_tab, load_icon("ic_finished.png"), "Finished")
        self.tabs.addTab(self.projects_tab, load_icon("ic_projects.png"), "Projects")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # forward signals
        for ttab in (self.today_tab, self.pending_tab, self.finished_tab):
            ttab.task_add_requested.connect(self.task_add_requested)
            ttab.task_edit_requested.connect(self.task_edit_requested)
            ttab.task_delete_requested.connect(self.task_delete_requested)
            ttab.task_status_changed.connect(self.task_status_changed)

        # Manual order changes (Today tab)
        self.today_tab.task_order_changed.connect(self.task_order_changed)

        # Projects signals
        self.projects_tab.project_add_requested.connect(self.project_add_requested)
        self.projects_tab.project_edit_requested.connect(self.project_edit_requested)
        self.projects_tab.project_delete_requested.connect(self.project_delete_requested)
        self.projects_tab.project_status_changed.connect(self.project_status_changed)

    def set_tasks(self, tasks: List[DailyTask]):
        self._all_tasks = list(tasks)
        self._apply_filters()

    def _apply_filters(self):
        tasks = self._all_tasks
        today = date.today()

        # Base selection for today tab: today's tasks + notes (notes always included)
        today_items = [t for t in tasks if (t.is_note or t.start_dt.date() == today)]

        filt = self.quick_filter.currentText() if hasattr(self, "quick_filter") else "All (Today)"
        status_map = {
            "Working only (Today)": TaskStatus.WORKING,
            "Unfinished only (Today)": TaskStatus.UNFINISHED,
            "Postponed only (Today)": TaskStatus.POSTPONED,
            "Finished only (Today)": TaskStatus.FINISHED,
        }
        if filt in status_map:
            target = status_map[filt]
            notes = [t for t in today_items if t.is_note]
            only = [t for t in today_items if (not t.is_note) and t.status == target]
            today_items = notes + only

        pending_tasks = [t for t in tasks if (not t.is_note) and t.status in (TaskStatus.UNFINISHED, TaskStatus.WORKING, TaskStatus.POSTPONED)]
        finished_tasks = [t for t in tasks if (not t.is_note) and t.status == TaskStatus.FINISHED]

        self.today_tab.set_tasks(today_items)
        self.pending_tab.set_tasks(pending_tasks)
        self.finished_tab.set_tasks(finished_tasks)

        # Dashboard
        try:
            self.dashboard_tab.set_data(tasks, getattr(self, "_all_projects", []))
        except Exception:
            pass


    def set_projects(self, projects: List[ProjectItem]):
        self._all_projects = list(projects)
        self.projects_tab.set_projects(self._all_projects)

        # Dashboard
        try:
            self.dashboard_tab.set_data(getattr(self, "_all_tasks", []), self._all_projects)
        except Exception:
            pass