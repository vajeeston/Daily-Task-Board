"""
Main window for Daily Task Board.
"""
from __future__ import annotations

import uuid
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import shutil

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QAction, QFileDialog, QMessageBox, QStatusBar, QStyle,
    QLabel, QSizePolicy, QHBoxLayout, QToolButton, QMenu, QActionGroup,
    QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QSystemTrayIcon
)
from PyQt5.QtCore import Qt, QSettings, QSize, QSizeF, QTimer, QStandardPaths
from PyQt5.QtGui import QIcon, QPixmap, QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

from icon_utils import load_icon, resource_path

from models import DailyTask, TaskStatus, ProjectItem
from storage_xlsx import load_data_xlsx, save_data_xlsx
from task_dialog import TaskDialog
from project_dialog import ProjectDialog
from notice_board import NoticeBoard
from calendar_panel import CalendarPanel


class ExportPdfOptionsDialog(QDialog):
    """Choose whether to include Details text and/or image thumbnails in PDF export."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export to PDF — Options")
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.cb_details = QCheckBox("Include Details text for each task/project")
        self.cb_details.setChecked(False)
        self.cb_thumbs = QCheckBox("Include image thumbnails from Details (if any)")
        self.cb_thumbs.setChecked(False)

        layout.addWidget(self.cb_details)
        layout.addWidget(self.cb_thumbs)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def options(self):
        return {
            "include_details": self.cb_details.isChecked(),
            "include_thumbnails": self.cb_thumbs.isChecked(),
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Daily Task Board")
        self.setGeometry(100, 100, 1200, 780)
        self._settings = QSettings("DailyTaskBoard", "DailyTaskBoard")

        self._set_window_icon()

        self.current_file: Optional[str] = None
        self.tasks: List[DailyTask] = []
        self.projects: List[ProjectItem] = []

        self._init_ui()
        self._apply_windows_theme()
        self._try_open_last_file()
        # If nothing is open yet, fall back to the default workbook location.
        self._open_or_create_default_workbook_if_needed()

        # Reminders / notifications (Tasks + Projects)
        self._setup_tray_and_reminders()

    # ---------- paths / icons ----------
    def _icon_path(self) -> Optional[str]:
        # Prefer bundled resources (works for PyInstaller) and fall back to local files.
        for name in (
            "app_icon.ico",
            "app_icon.png",
            "assets/app_icon.ico",
            "assets/app_icon.png",
        ):
            p = resource_path(*name.split("/"))
            if p.exists():
                return str(p)
        return None

    def _set_window_icon(self) -> None:
        ip = self._icon_path()
        if ip:
            icon = QIcon(ip)
            self.setWindowIcon(icon)
            app = QApplication.instance()
            if app is not None:
                app.setWindowIcon(icon)

    def _manual_path(self) -> Optional[str]:
        """Return the bundled HTML manual path if present."""
        # Prefer docs/user_manual.html shipped with the project.
        for cand in (
            ("docs", "user_manual.html"),
            ("docs", "index.html"),
            ("user_manual.html",),
        ):
            p = resource_path(*cand)
            if p.exists():
                return str(p)
        return None

    # ---------- default workbook location (Settings) ----------
    def _project_dir(self) -> Path:
        # In a PyInstaller build, __file__ points inside the temporary bundle.
        # Use the executable directory as the "project" dir for user-visible paths.
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    def _app_data_dir(self) -> Path:
        """Writable per-user data directory (best default for an installed .exe)."""
        p = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not p:
            p = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        base = Path(p) if p else Path.home() / "Documents"
        # Keep it tidy: ensure a folder exists.
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _storage_dir(self) -> Path:
        """Return the user-chosen storage dir (or project dir by default)."""
        mode = self._settings.value("storage_mode", "project", type=str)
        custom = self._settings.value("storage_custom_dir", "", type=str)
        if mode == "custom" and custom:
            p = Path(custom)
            if p.exists():
                return p
        # If running as an .exe, the install folder may be read-only.
        if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
            return self._app_data_dir()
        return self._project_dir()

    def _default_workbook_path(self) -> Path:
        return self._storage_dir() / "daily_tasks.xlsx"

    def _open_or_create_default_workbook_if_needed(self, force: bool = False) -> None:
        """Open last file if present; otherwise open/create the default workbook.

        If force=True, switches to the default workbook even if a different file is currently open.
        """
        if self.current_file and not force:
            return

        target = self._default_workbook_path()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If custom dir is invalid/unwritable, fall back to project dir.
            target = (self._project_dir() / "daily_tasks.xlsx")

        if target.exists():
            self._load_from(str(target))
            return

        # First-run experience:
        # - If a bundled sample workbook exists, copy it to the writable storage dir.
        # - Otherwise create an empty workbook.
        try:
            sample = resource_path("daily_tasks.xlsx")
            if sample.exists():
                shutil.copy2(str(sample), str(target))
                self._load_from(str(target))
                return
        except Exception:
            pass

        try:
            save_data_xlsx(str(target), [], [])
            self._load_from(str(target))
        except Exception as e:
            QMessageBox.warning(self, "Create file failed", f"Could not create default file:\n{e}")

    def show_user_manual(self):
        """Open the built-in user manual (HTML) in a help window."""
        from help_dialog import HelpDialog  # local import to keep startup fast

        manual = self._manual_path()
        dlg = HelpDialog(self, html_path=manual)
        dlg.exec_()

    # ---------------- Reminders / notifications ----------------
    def _setup_tray_and_reminders(self) -> None:
        """Create a system tray icon + start the reminder timer.

        Windows shows desktop notifications via the tray icon.
        """
        if hasattr(self, "_reminder_timer"):
            return

        ip = self._icon_path()
        icon = QIcon(ip) if ip else self.style().standardIcon(QStyle.SP_MessageBoxInformation)

        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("Daily Task Board")
        self._tray.setVisible(True)

        # Small tray menu
        m = QMenu()
        a_show = QAction("Show", self)
        a_show.triggered.connect(self.showNormal)
        m.addAction(a_show)
        a_quit = QAction("Quit", self)
        a_quit.triggered.connect(self.close)
        m.addAction(a_quit)
        self._tray.setContextMenu(m)

        # Timer interval (user requested 60s)
        self._reminder_timer = QTimer(self)
        self._reminder_timer.setInterval(60 * 1000)
        self._reminder_timer.timeout.connect(self._check_reminders)
        self._reminder_timer.start()

        # Also check once on startup
        QTimer.singleShot(1500, self._check_reminders)

    def _first_line_from_details(self, details_html: str) -> str:
        if not details_html:
            return ""
        doc = QTextDocument()
        doc.setHtml(details_html)
        text = doc.toPlainText().strip()
        if not text:
            return ""
        for line in text.splitlines():
            s = line.strip()
            if s:
                return s
        return ""

    def _show_notification(self, title: str, body: str) -> None:
        try:
            if hasattr(self, "_tray") and self._tray is not None:
                self._tray.showMessage(title, body, QSystemTrayIcon.Information, 10_000)
        except Exception:
            # Non-fatal
            pass

    def _check_reminders(self) -> None:
        """Check reminders for tasks and projects.

        Conditions:
        - Skip Finished/Postponed items.
        - Trigger if now is within 5 minutes after the reminder time.
        - Store sent flags to avoid duplicates across restarts.
        """
        now = datetime.now()
        window_seconds = 5 * 60

        def should_fire(target_dt: Optional[datetime]) -> bool:
            if not target_dt:
                return False
            delta = (now - target_dt).total_seconds()
            return 0 <= delta <= window_seconds

        any_changed = False

        # --- tasks ---
        for t in self.tasks:
            if getattr(t, "is_note", False):
                continue
            if t.status in (TaskStatus.FINISHED, TaskStatus.POSTPONED):
                continue
            base = getattr(t, "due_dt", None) or t.start_dt
            if not base:
                continue

            msg_line = self._first_line_from_details(getattr(t, "details_html", ""))
            if msg_line:
                msg_line = msg_line.strip()

            if getattr(t, "remind_1h", False) and not getattr(t, "sent_1h", False):
                if should_fire(base - timedelta(hours=1)):
                    self._show_notification(t.title, f"In 1 hour — {msg_line}" if msg_line else "In 1 hour")
                    t.sent_1h = True
                    any_changed = True

            if getattr(t, "remind_10m", False) and not getattr(t, "sent_10m", False):
                if should_fire(base - timedelta(minutes=10)):
                    self._show_notification(t.title, f"In 10 minutes — {msg_line}" if msg_line else "In 10 minutes")
                    t.sent_10m = True
                    any_changed = True

            if getattr(t, "remind_at", False) and not getattr(t, "sent_at", False):
                if should_fire(base):
                    self._show_notification(t.title, msg_line if msg_line else "Time")
                    t.sent_at = True
                    any_changed = True

        # --- projects ---
        for p in self.projects:
            if p.status in (TaskStatus.FINISHED, TaskStatus.POSTPONED):
                continue
            base = getattr(p, "reminder_dt", None)
            if not base:
                continue

            msg_line = self._first_line_from_details(getattr(p, "details_html", ""))
            if msg_line:
                msg_line = msg_line.strip()

            if getattr(p, "remind_1h", False) and not getattr(p, "sent_1h", False):
                if should_fire(base - timedelta(hours=1)):
                    self._show_notification(p.title, f"In 1 hour — {msg_line}" if msg_line else "In 1 hour")
                    p.sent_1h = True
                    any_changed = True

            if getattr(p, "remind_10m", False) and not getattr(p, "sent_10m", False):
                if should_fire(base - timedelta(minutes=10)):
                    self._show_notification(p.title, f"In 10 minutes — {msg_line}" if msg_line else "In 10 minutes")
                    p.sent_10m = True
                    any_changed = True

            if getattr(p, "remind_at", False) and not getattr(p, "sent_at", False):
                if should_fire(base):
                    self._show_notification(p.title, msg_line if msg_line else "Time")
                    p.sent_at = True
                    any_changed = True

        if any_changed:
            self._auto_save()

    # ---------------- UI ----------------
    def _init_ui(self):
        self._create_menu()
        self._create_toolbar()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Right-side copyright (permanent)
        self._copyright_label = QLabel(f"© {datetime.now().year} Daily Task Board. All rights reserved.")
        self._copyright_label.setObjectName("CopyrightLabel")
        self.status_bar.addPermanentWidget(self._copyright_label)

        splitter = QSplitter(Qt.Horizontal)

        self.calendar_panel = CalendarPanel()
        self.notice_board = NoticeBoard()

        splitter.addWidget(self.calendar_panel)
        splitter.addWidget(self.notice_board)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

        # Signals
        self.calendar_panel.add_task_for_date.connect(self.add_task)
        self.calendar_panel.edit_task_requested.connect(self.edit_task)
        self.calendar_panel.task_move_requested.connect(self.move_task_to_date)

        self.notice_board.task_add_requested.connect(lambda _: self.add_task(None))
        self.notice_board.task_edit_requested.connect(self.edit_task)
        self.notice_board.task_delete_requested.connect(self.delete_task)
        self.notice_board.task_status_changed.connect(self.change_status)
        self.notice_board.task_order_changed.connect(self.on_task_order_changed)

        # Projects (Projects tab)
        self.notice_board.project_add_requested.connect(lambda _: self.add_project(None))
        self.notice_board.project_edit_requested.connect(self.edit_project)
        self.notice_board.project_delete_requested.connect(self.delete_project)
        self.notice_board.project_status_changed.connect(self.on_project_status_changed)

        self.refresh_views()

    def _create_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")

        new_act = QAction(load_icon("ic_new.png"), "&New", self)
        new_act.setShortcut("Ctrl+N")
        new_act.triggered.connect(self.new_file)
        file_menu.addAction(new_act)

        open_act = QAction(load_icon("ic_open.png"), "&Open...", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self.open_file)
        file_menu.addAction(open_act)

        save_act = QAction(load_icon("ic_save.png"), "&Save", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self.save_file)
        file_menu.addAction(save_act)

        save_as_act = QAction(load_icon("ic_save_as.png"), "Save &As...", self)
        save_as_act.setShortcut("Ctrl+Shift+S")
        save_as_act.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        print_act = QAction(load_icon("ic_print.png"), "&Print…", self)
        print_act.setShortcut("Ctrl+P")
        print_act.triggered.connect(self.print_all_sheets)
        file_menu.addAction(print_act)

        export_pdf_act = QAction(load_icon("ic_export_pdf.png"), "Export all sheets to &PDF…", self)
        export_pdf_act.triggered.connect(self.export_all_sheets_to_pdf)
        file_menu.addAction(export_pdf_act)

        restore_act = QAction(load_icon("ic_restore.png"), "Restore from &backup…", self)
        restore_act.triggered.connect(self.restore_from_backup)
        file_menu.addAction(restore_act)

        file_menu.addSeparator()

        exit_act = QAction("E&xit", self)
        exit_act.setShortcut("Ctrl+Q")
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Settings
        settings_menu = mb.addMenu("&Settings")
        storage_act = QAction("Default file &location…", self)
        storage_act.triggered.connect(self.open_settings)
        settings_menu.addAction(storage_act)


        # Help
        help_menu = mb.addMenu("&Help")
        manual_act = QAction("User &Manual", self)
        manual_act.setShortcut("F1")
        manual_act.triggered.connect(self.show_user_manual)
        help_menu.addAction(manual_act)

    # ---------------- Printing / PDF export ----------------
    def _build_all_sheets_html(self, include_details: bool = False, include_thumbnails: bool = False) -> str:
        """Build a printable HTML document containing all 'sheets' (tasks by status + projects).

        By default this exports a clean summary. If requested, it can include:
        - Details text per task/project
        - Image thumbnails extracted from Details (if any)
        """
        from datetime import datetime

        def fmt_dt(dt: Optional[datetime]) -> str:
            if not dt:
                return ""
            try:
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                return str(dt)

        def esc(s: str) -> str:
            return (
                str(s)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

        def render_table(headers: List[str], rows: List[List[str]], raw_cols: Optional[List[int]] = None) -> str:
            """Render a simple HTML table.

            raw_cols: column indexes that contain raw HTML (not escaped), used for thumbnail cells.
            """
            raw = set(raw_cols or [])
            th = "".join(f"<th>{esc(h)}</th>" for h in headers)
            body = []
            for r in rows:
                tds_parts = []
                for i, c in enumerate(r):
                    if i in raw:
                        tds_parts.append(f"<td>{c}</td>")
                    else:
                        tds_parts.append(f"<td>{esc(c)}</td>")
                body.append(f"<tr>{''.join(tds_parts)}</tr>")
            return (
                "<table>"
                f"<thead><tr>{th}</tr></thead>"
                f"<tbody>{''.join(body)}</tbody>"
                "</table>"
            )

        def html_to_text(html: str) -> str:
            if not html:
                return ""
            doc = QTextDocument()
            doc.setHtml(html)
            return doc.toPlainText().strip()

        def extract_img_srcs(html: str) -> List[str]:
            if not html:
                return []
            import re
            srcs = re.findall(r"<img[^>]+src=[\"\']([^\"\']+)[\"\']", html, flags=re.IGNORECASE)
            out: List[str] = []
            for s in srcs:
                s = (s or "").strip()
                if not s:
                    continue
                if s.startswith("file:") or s.startswith("http:") or s.startswith("https:"):
                    out.append(s)
                    continue
                # Convert absolute local paths to file:/// URIs when possible
                try:
                    p = Path(s)
                    if p.exists():
                        out.append(p.as_uri())
                    else:
                        out.append(s)
                except Exception:
                    out.append(s)
            return out

        def build_thumbs_html(details_html: str, max_imgs: int = 4, thumb_w: int = 120) -> str:
            srcs = extract_img_srcs(details_html)[:max_imgs]
            if not srcs:
                return ""
            # NOTE: use width attribute; Qt5 respects it more reliably than CSS max-width.
            parts = []
            for s in srcs:
                safe_src = esc(s)
                parts.append(
                    f"<div style='margin-bottom:6px;'>"
                    f"<img src='{safe_src}' width='{thumb_w}' style='border:1px solid #e5e7eb;border-radius:8px;'/>"
                    f"</div>"
                )
            return f"<div class='thumbcell'>{''.join(parts)}</div>"

        # ---- Build sheet sections ----
        now = datetime.now()
        file_label = Path(self.current_file).name if self.current_file else "(unsaved)"

        task_headers = ["Title", "Status", "Start", "Finished", "Note", "Attachments"]
        if include_details:
            task_headers.append("Details")
        if include_thumbnails:
            task_headers.append("Thumbnails")

        def task_rows(task_list: List[DailyTask]) -> List[List[str]]:
            out: List[List[str]] = []
            for t in sorted(task_list, key=lambda x: x.start_dt):
                attachments = "\n".join(t.attachments or [])
                row = [
                    t.title or "",
                    t.status.value,
                    fmt_dt(t.start_dt),
                    fmt_dt(t.finished_dt),
                    "Yes" if t.is_note else "",
                    attachments,
                ]
                if include_details:
                    row.append(html_to_text(t.details_html or ""))
                if include_thumbnails:
                    row.append(build_thumbs_html(t.details_html or ""))
                out.append(row)
            return out

        all_tasks = [t for t in self.tasks]
        unfinished = [t for t in all_tasks if (not t.is_note) and t.status == TaskStatus.UNFINISHED]
        working = [t for t in all_tasks if (not t.is_note) and t.status == TaskStatus.WORKING]
        postponed = [t for t in all_tasks if (not t.is_note) and t.status == TaskStatus.POSTPONED]
        finished = [t for t in all_tasks if (not t.is_note) and t.status == TaskStatus.FINISHED]
        notes = [t for t in all_tasks if t.is_note]

        sections = []

        def add_section(title: str, subtitle: str, table_html: str, page_break: bool = False):
            pb = "page-break-before: always;" if page_break else ""
            sections.append(
                f"<div class='sheet' style='{pb}'>"
                f"<h1>{esc(title)}</h1>"
                f"<div class='meta'>{esc(subtitle)}</div>"
                f"{table_html}"
                "</div>"
            )

        base_meta = f"File: {file_label} — Exported: {now.strftime('%Y-%m-%d %H:%M')}"
        thumb_col = (len(task_headers) - 1) if include_thumbnails else None
        raw_cols = [thumb_col] if thumb_col is not None else []

        add_section("Tasks (All)", base_meta, render_table(task_headers, task_rows(all_tasks), raw_cols=raw_cols), page_break=False)
        add_section("Tasks (Unfinished)", base_meta, render_table(task_headers, task_rows(unfinished), raw_cols=raw_cols), page_break=True)
        add_section("Tasks (Working)", base_meta, render_table(task_headers, task_rows(working), raw_cols=raw_cols), page_break=True)
        add_section("Tasks (Postponed)", base_meta, render_table(task_headers, task_rows(postponed), raw_cols=raw_cols), page_break=True)
        add_section("Tasks (Finished)", base_meta, render_table(task_headers, task_rows(finished), raw_cols=raw_cols), page_break=True)
        add_section("Notes", base_meta, render_table(task_headers, task_rows(notes), raw_cols=raw_cols), page_break=True)

        # Projects
        proj_headers = ["Title", "Status", "Code path", "Links", "Updated", "Finished", "Attachments"]
        if include_details:
            proj_headers.append("Details")
        if include_thumbnails:
            proj_headers.append("Thumbnails")
        proj_rows: List[List[str]] = []
        for p in sorted(self.projects, key=lambda x: (x.updated_dt or datetime.min), reverse=True):
            links = "\n".join(p.links or [])
            attachments = "\n".join(p.attachments or [])
            prow = [
                p.title or "",
                p.status.value,
                p.code_path or "",
                links,
                fmt_dt(p.updated_dt),
                fmt_dt(p.finished_dt),
                attachments,
            ]
            if include_details:
                prow.append(html_to_text(p.details_html or ""))
            if include_thumbnails:
                prow.append(build_thumbs_html(p.details_html or ""))
            proj_rows.append(prow)

        p_thumb_col = (len(proj_headers) - 1) if include_thumbnails else None
        p_raw_cols = [p_thumb_col] if p_thumb_col is not None else []
        add_section("Projects", base_meta, render_table(proj_headers, proj_rows, raw_cols=p_raw_cols), page_break=True)

        # ---- Full HTML ----
        html = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #111827; }}
    h1 {{ font-size: 16pt; margin: 0 0 6px 0; }}
    .meta {{ color: #6b7280; font-size: 9pt; margin-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 6px 8px; vertical-align: top; word-wrap: break-word; white-space: pre-wrap; }}
    th {{ background: #f3f4f6; font-weight: 700; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    .thumbcell {{ text-align: center; }}
    .sheet {{ margin-bottom: 18px; }}
  </style>
</head>
<body>
  {''.join(sections)}
</body>
</html>"""
        return html

    def _print_html_to_printer(self, printer: QPrinter, html: str) -> None:
        doc = QTextDocument()
        doc.setHtml(html)
        # Make sure the document paginates properly for the target device
        # QTextDocument.setPageSize expects QSizeF in PyQt5.
        doc.setPageSize(QSizeF(printer.pageRect().size()))
        doc.print_(printer)

    def export_all_sheets_to_pdf(self) -> None:
        """Export all app 'sheets' to a single PDF (page breaks between sections)."""
        # Ensure current state is saved into the workbook if we have a path
        try:
            self.save_file()
        except Exception:
            # save_file() already shows errors
            pass

        # Ask what content to include
        opt_dlg = ExportPdfOptionsDialog(self)
        if opt_dlg.exec_() != QDialog.Accepted:
            return
        opts = opt_dlg.options()

        default = "daily_task_board.pdf"
        if self.current_file:
            default = str(Path(self.current_file).with_suffix(".pdf"))

        filename, _ = QFileDialog.getSaveFileName(self, "Export to PDF", default, "PDF Files (*.pdf)")
        if not filename:
            return
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(filename)
            printer.setOrientation(QPrinter.Landscape)
            html = self._build_all_sheets_html(
                include_details=opts.get("include_details", False),
                include_thumbnails=opts.get("include_thumbnails", False),
            )
            self._print_html_to_printer(printer, html)
            self.status_bar.showMessage(f"Exported PDF: {filename}", 5000)
        except Exception as e:
            QMessageBox.warning(self, "Export failed", f"Could not export PDF:\n{e}")

    def print_all_sheets(self) -> None:
        """Print all app 'sheets' using the system print dialog."""
        try:
            self.save_file()
        except Exception:
            pass

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOrientation(QPrinter.Landscape)
        dlg = QPrintDialog(printer, self)
        dlg.setWindowTitle("Print — Daily Task Board")
        if dlg.exec_() != dlg.Accepted:
            return
        try:
            html = self._build_all_sheets_html()
            self._print_html_to_printer(printer, html)
        except Exception as e:
            QMessageBox.warning(self, "Print failed", f"Could not print:\n{e}")

    def _create_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(40, 36))

        style = self.style()

        a_new = QAction(load_icon("ic_new.png"), "New", self)
        a_new.setShortcut("Ctrl+N")
        a_new.triggered.connect(self.new_file)
        tb.addAction(a_new)

        a_open = QAction(load_icon("ic_open.png"), "Open", self)
        a_open.setShortcut("Ctrl+O")
        a_open.triggered.connect(self.open_file)
        tb.addAction(a_open)

        a_save = QAction(load_icon("ic_save.png"), "Save", self)
        a_save.setShortcut("Ctrl+S")
        a_save.triggered.connect(self.save_file)
        tb.addAction(a_save)

        # Settings (default workbook location)
        a_settings = QAction(load_icon("ic_settings.png"), "Settings", self)
        a_settings.triggered.connect(self.open_settings)
        tb.addAction(a_settings)

        tb.addSeparator()

        # Help + Close (requested)
        a_help = QAction(load_icon("ic_help.png"), "Help", self)
        a_help.setShortcut("F1")
        a_help.triggered.connect(self.show_user_manual)
        tb.addAction(a_help)

        a_close = QAction(load_icon("ic_close.png"), "Close", self)
        a_close.setShortcut("Ctrl+Q")
        a_close.triggered.connect(self.close)
        tb.addAction(a_close)


        # Spacer pushes the banner to the far right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        # Banner (top-right) — image
        banner_lbl = QLabel()
        banner_lbl.setObjectName("TopBanner")
        banner_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        banner_path = resource_path("assets", "banner.png")
        if banner_path.exists():
            pm = QPixmap(str(banner_path))
            # Keep the toolbar compact but readable
            target_h = 80
            banner_lbl.setPixmap(pm.scaledToHeight(target_h, Qt.SmoothTransformation))
            banner_lbl.setFixedHeight(target_h)
        else:
            # Fallback to text if the banner image is missing
            banner_lbl.setText("Daily Task Board")
            banner_lbl.setStyleSheet("font-weight:700; padding:6px 10px;")

        tb.addWidget(banner_lbl)


    # ---------------- Style (Windows only) ----------------
    def _apply_windows_theme(self):
        # Apply WindowsVista style + the app's accent stylesheet
        app = QApplication.instance()
        if app is None:
            return
        app.setStyle("WindowsVista")
        app.setStyleSheet(self._build_qss())

        # Ensure widgets that depend on dynamic properties refresh correctly
        self.refresh_views()

    def _build_qss(self) -> str:
        # Windows theme: keep native look, apply only key improvements + status colors.
        return r"""
        * { font-family: "Segoe UI"; font-size: 10pt; }

        QStatusBar::item { border: none; }
        QLabel#CopyrightLabel { color: #6b7280; padding-right: 10px; }

        /* Calendar: bold day numbers */
        QCalendarWidget QAbstractItemView { font-weight: 700; }

        /* Make "Tasks on selected date:" label a bit bolder */
        QLabel#TasksSelectedLabel { font-weight: 700; }

        /* Table readability */
        QTableWidget { gridline-color: #fbcfe8; }
        QTableWidget { selection-background-color: #dbeafe; selection-color: #111827; }
        QHeaderView::section {
            background: #f3f4f6;
            padding: 8px;
            border: none;
            border-bottom: 1px solid #e5e7eb;
            font-weight: 700;
        }

        /* Accent buttons */
        QPushButton {
            background: #ffffff;
            color: #111827;
            border: 1px solid #d1d5db;
            padding: 7px 12px;
            border-radius: 12px;
        }
        QPushButton:hover { background: #f3f4f6; }
        QPushButton:pressed { background: #e5e7eb; }

        QPushButton#PrimaryButton {
            background: #2563eb;
            color: #ffffff;
            border: 1px solid #2563eb;
        }
        QPushButton#PrimaryButton:hover { background: #1d4ed8; border-color: #1d4ed8; }

        QPushButton#SecondaryButton {
            background: #ffffff;
            color: #111827;
            border: 1px solid #d1d5db;
        }

        QPushButton#DangerButton {
            background: #ffffff;
            color: #b91c1c;
            border: 1px solid #fecaca;
        }
        QPushButton#DangerButton:hover { background: #fef2f2; }

        /* Top-right banner */
        QLabel#TopBanner { padding: 0px; margin: 0px; }

        /* NoticeBoard tabs: inactive = light red, active = light green */
        QTabWidget#NoticeTabs::pane { top: -1px; border-radius: 14px; }
        QTabWidget#NoticeTabs QTabBar::tab {
            background: #ffe4e6;
            border: 1px solid #fecdd3;
            border-bottom: none;
            padding: 8px 14px;
            margin-right: 6px;
            border-top-left-radius: 14px;
            border-top-right-radius: 14px;
        }
        QTabWidget#NoticeTabs QTabBar::tab:selected {
            background: #dcfce7;
            border-color: #bbf7d0;
            font-weight: 800;
        }

        /* Status legend */
        QFrame#LegendFrame { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; }
        QLabel#LegendPill { border-radius: 999px; padding: 4px 10px; font-weight: 700; }
        QLabel#LegendPill[status="Unfinished"] { background: #ffe4e6; border: 1px solid #fecdd3; color: #111827; }
        QLabel#LegendPill[status="Working"]    { background: #dbeafe; border: 1px solid #bfdbfe; color: #111827; }
        QLabel#LegendPill[status="Postponed"]  { background: #fef3c7; border: 1px solid #fde68a; color: #111827; }
        QLabel#LegendPill[status="Finished"]   { background: #dcfce7; border: 1px solid #bbf7d0; color: #111827; }

        /* Quick filter */
        QComboBox#QuickFilter { min-height: 30px; border-radius: 12px; padding: 6px 10px; }

        /* Digital clock (modern pill) */
        QLabel#DigitalClock {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f3f4f6);
            border: 1px solid #cbd5e1;
            color: #111827;
            border-radius: 999px;
            padding: 6px 16px;
            font-weight: 900;
            font-family: Consolas, "Segoe UI", monospace;
            font-size: 14px;
        }

        /* Stopwatch (modern pill) */
        QWidget#StopwatchWidget {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f3f4f6);
            border: 1px solid #cbd5e1;
            border-radius: 999px;
        }
        QLabel#StopwatchLabel {
            color: #111827;
            font-weight: 900;
            font-family: Consolas, "Segoe UI", monospace;
        }
        QToolButton#StopwatchToggle, QToolButton#StopwatchReset {
            background: transparent;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 4px;
        }
        QToolButton#StopwatchToggle:hover, QToolButton#StopwatchReset:hover {
            background: #eef2ff;
        }

        /* Status combo (visible + colored by status) */
        QComboBox#StatusCombo {
            border-radius: 10px;
            padding: 4px 10px;
            min-height: 24px;
            color: #111827;
        }
        QComboBox#StatusCombo::drop-down { border: 0px; width: 20px; }
        QComboBox#StatusCombo[taskStatus="Unfinished"] { background: #ffe4e6; border: 1px solid #fecdd3; }
        QComboBox#StatusCombo[taskStatus="Working"]    { background: #dbeafe; border: 1px solid #bfdbfe; }
        QComboBox#StatusCombo[taskStatus="Postponed"]  { background: #fef3c7; border: 1px solid #fde68a; }
        QComboBox#StatusCombo[taskStatus="Finished"]   { background: #dcfce7; border: 1px solid #bbf7d0; }
        """

    # ---------------- Data ops ----------------
    def refresh_views(self):
        self.calendar_panel.set_tasks(self.tasks)
        self.notice_board.set_tasks(self.tasks)
        self.notice_board.set_projects(self.projects)
        self._update_statusbar()

    def _refresh_views(self):
        """Backward-compatible alias for older code paths."""
        self.refresh_views()

    def _update_statusbar(self):
        total = len([t for t in self.tasks if not t.is_note])
        finished = len([t for t in self.tasks if (not t.is_note) and t.status == TaskStatus.FINISHED])
        pending = len([t for t in self.tasks if (not t.is_note) and t.status in (TaskStatus.UNFINISHED, TaskStatus.WORKING, TaskStatus.POSTPONED)])
        self.status_bar.showMessage(f"Tasks: {total}   Pending: {pending}   Finished: {finished}   Projects: {len(self.projects)}   File: {self.current_file or '—'}")

    def _auto_save(self):
        if not self.current_file:
            # Fall back to default workbook location if none is open.
            self.current_file = str(self._default_workbook_path())
        try:
            save_data_xlsx(self.current_file, self.tasks, self.projects)
            self._maybe_create_backup()
        except Exception as e:
            QMessageBox.warning(self, "Save failed", str(e))

    # ---------------- Backup / versioning ----------------
    def _backup_dir(self) -> Path:
        """Backups live next to the workbook in a 'backups' folder."""
        try:
            base = Path(self.current_file).resolve().parent if self.current_file else self._storage_dir()
        except Exception:
            base = self._storage_dir()
        return base / "backups"

    def _maybe_create_backup(self) -> None:
        """Keep a daily backup copy: daily_tasks_backup_YYYY-MM-DD.xlsx

        - Only one backup per day.
        - Keep last N backups (default 30).
        """
        if not self.current_file:
            return

        bdir = self._backup_dir()
        try:
            bdir.mkdir(parents=True, exist_ok=True)
        except Exception:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        backup_name = f"daily_tasks_backup_{today}.xlsx"
        bpath = bdir / backup_name
        if not bpath.exists():
            try:
                shutil.copy2(self.current_file, str(bpath))
            except Exception:
                pass

        # prune
        keep_n = self._settings.value("backup_keep_n", 30, type=int)
        self._prune_backups(keep_n)

    def _prune_backups(self, keep_n: int = 30) -> None:
        bdir = self._backup_dir()
        if not bdir.exists():
            return
        files = sorted(bdir.glob("daily_tasks_backup_*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in files[keep_n:]:
            try:
                p.unlink()
            except Exception:
                pass

    def restore_from_backup(self) -> None:
        """Restore from a backup workbook."""
        bdir = str(self._backup_dir())
        filename, _ = QFileDialog.getOpenFileName(self, "Restore from backup", bdir, "Excel Files (*.xlsx)")
        if not filename:
            return

        if not self.current_file:
            self.current_file = str(self._default_workbook_path())

        resp = QMessageBox.question(
            self,
            "Restore backup",
            "This will replace your current workbook with the selected backup. Continue?",
        )
        if resp != QMessageBox.Yes:
            return
        try:
            shutil.copy2(filename, self.current_file)
            self._load_from(self.current_file)
            self.status_bar.showMessage("Restored from backup.", 5000)
        except Exception as e:
            QMessageBox.warning(self, "Restore failed", str(e))

    def new_file(self):
        self.tasks = []
        self.projects = []
        self.current_file = None
        self._settings.setValue("last_file", "")
        self.refresh_views()

    def open_file(self):
        start_dir = str(self._storage_dir())
        filename, _ = QFileDialog.getOpenFileName(self, "Open Task File", start_dir, "Excel Files (*.xlsx)")
        if not filename:
            return
        self._load_from(filename)

    def _try_open_last_file(self):
        last = self._settings.value("last_file", "", type=str)
        if last and Path(last).exists():
            self._load_from(last)

    def _load_from(self, filename: str):
        try:
            self.tasks, self.projects = load_data_xlsx(filename)
            self.current_file = filename
            self._settings.setValue("last_file", filename)
            self.refresh_views()
        except Exception as e:
            QMessageBox.warning(self, "Open failed", f"Could not open file:\n{e}")

    def save_file(self):
        if not self.current_file:
            return self.save_file_as()
        try:
            save_data_xlsx(self.current_file, self.tasks, self.projects)
            self.status_bar.showMessage(f"Saved: {self.current_file}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Save failed", str(e))

    def save_file_as(self):
        start = str(self._default_workbook_path())
        filename, _ = QFileDialog.getSaveFileName(self, "Save Task File As", start, "Excel Files (*.xlsx)")
        if not filename:
            return
        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"
        self.current_file = filename
        self._settings.setValue("last_file", filename)
        self.save_file()

    # ---------------- Settings ----------------
    def open_settings(self):
        """Choose where the default workbook is stored (project folder or OneDrive/custom)."""
        from settings_dialog import SettingsDialog  # local import

        dlg = SettingsDialog(
            self,
            project_dir=str(self._project_dir()),
            mode=self._settings.value("storage_mode", "project", type=str),
            custom_dir=self._settings.value("storage_custom_dir", "", type=str),
        )
        if dlg.exec_() != dlg.Accepted:
            return

        self._settings.setValue("storage_mode", dlg.chosen_mode())
        self._settings.setValue("storage_custom_dir", dlg.chosen_custom_dir())

        # Switch to the default workbook in the newly selected location.
        self._open_or_create_default_workbook_if_needed(force=True)

    
    # ---------------- Projects ----------------
    def add_project(self, _default=None):
        dlg = ProjectDialog(self, project=None)
        if dlg.exec_() == dlg.Accepted:
            p = dlg.build_project()
            # replace if exists (should not), else append
            self.projects = [x for x in self.projects if x.id != p.id] + [p]
            self._refresh_views()
            self._auto_save()

    def edit_project(self, project_id: str):
        prj = next((x for x in self.projects if x.id == project_id), None)
        if not prj:
            return
        dlg = ProjectDialog(self, project=prj)
        if dlg.exec_() == dlg.Accepted:
            updated = dlg.build_project()
            self.projects = [x for x in self.projects if x.id != updated.id] + [updated]
            self._refresh_views()
            self._auto_save()

    def delete_project(self, project_id: str):
        self.projects = [x for x in self.projects if x.id != project_id]
        self._refresh_views()
        self._auto_save()

    def on_project_status_changed(self, project_id: str, new_status_text: str):
        from datetime import datetime
        try:
            new_status = TaskStatus(new_status_text)
        except Exception:
            return
        for p in self.projects:
            if p.id == project_id:
                p.mark_status(new_status, now=datetime.now())
                break
        self._refresh_views()
        self._auto_save()

    def add_task(self, default_start):
        dlg = TaskDialog(self, task=None, default_start=default_start)
        if dlg.exec_() == dlg.Accepted:
            t = dlg.build_task()
            # Ensure unique id
            if any(x.id == t.id for x in self.tasks):
                t.id = str(uuid.uuid4())
            self.tasks.append(t)
            self.refresh_views()
            self._auto_save()

    def edit_task(self, task_id: str):
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return
        dlg = TaskDialog(self, task=task, default_start=task.start_dt)
        if dlg.exec_() == dlg.Accepted:
            new_t = dlg.build_task()
            # Preserve id
            for i, t in enumerate(self.tasks):
                if t.id == task_id:
                    self.tasks[i] = new_t
                    break
            self.refresh_views()
            self._auto_save()

    def delete_task(self, task_id: str):
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return
        resp = QMessageBox.question(self, "Delete task", f"Delete '{task.title}'?")
        if resp != QMessageBox.Yes:
            return
        self.tasks = [t for t in self.tasks if t.id != task_id]
        self.refresh_views()
        self._auto_save()

    def move_task_to_date(self, task_id: str, new_date):
        """Drag & drop scheduling from the calendar list to a new day."""
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return
        try:
            # Keep time, change date.
            dt = task.start_dt
            task.start_dt = datetime(new_date.year, new_date.month, new_date.day, dt.hour, dt.minute, dt.second)
            # manual ordering is per-day; reset
            if hasattr(task, "order"):
                task.order = 0
            # rescheduling should re-arm reminders
            if hasattr(task, "reset_reminder_sent_flags"):
                task.reset_reminder_sent_flags()
        except Exception:
            return
        self.refresh_views()
        self._auto_save()

    def change_status(self, task_id: str, status_text: str):
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return
        try:
            new_status = TaskStatus(status_text)
        except Exception:
            return
        task.mark_status(new_status, now=datetime.now())
        self.refresh_views()
        self._auto_save()

    def on_task_order_changed(self, ordered_ids: list):
        """Persist manual ordering from the Today tab."""
        if not ordered_ids:
            return
        id_to_task = {t.id: t for t in self.tasks}
        for idx, tid in enumerate(ordered_ids, start=1):
            t = id_to_task.get(str(tid))
            if t is not None:
                try:
                    t.order = idx
                except Exception:
                    pass
        self.refresh_views()
        self._auto_save()