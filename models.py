"""
Models for Daily Task Board.

Core entities:
- DailyTask: calendar-based tasks (and optional notes)
- ProjectItem: a lightweight entry for your small tools/scripts

Status:
- Unfinished / Working / Postponed / Finished

Reminders (Tasks + Projects):
- Optional reminders at the base time, 10 minutes before, and/or 1 hour before.
- Sent flags are stored so reminders don't repeat after restart.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any


class TaskStatus(str, Enum):
    UNFINISHED = "Unfinished"
    WORKING = "Working"
    POSTPONED = "Postponed"
    FINISHED = "Finished"


def _parse_bool(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "y", "on")


def _parse_dt(v: Any) -> Optional[datetime]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v))
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(str(v), fmt)
            except Exception:
                continue
        return None


@dataclass
class DailyTask:
    id: str
    title: str
    start_dt: datetime
    status: TaskStatus = TaskStatus.UNFINISHED
    due_dt: Optional[datetime] = None
    order: int = 0

    details_html: str = ""
    finished_dt: Optional[datetime] = None
    is_note: bool = False
    attachments: List[str] = field(default_factory=list)

    # Reminder settings
    remind_at: bool = False
    remind_10m: bool = False
    remind_1h: bool = False
    sent_at: bool = False
    sent_10m: bool = False
    sent_1h: bool = False

    def base_reminder_dt(self) -> Optional[datetime]:
        return self.due_dt or self.start_dt

    def reset_reminder_sent_flags(self) -> None:
        self.sent_at = False
        self.sent_10m = False
        self.sent_1h = False

    def mark_status(self, new_status: TaskStatus, now: Optional[datetime] = None) -> None:
        now = now or datetime.now()
        if new_status == TaskStatus.FINISHED:
            if self.finished_dt is None:
                self.finished_dt = now
        else:
            self.finished_dt = None
        self.status = new_status

    def start_date(self):
        return self.start_dt.date()

    def to_row(self):
        return [
            self.id,
            self.title,
            self.status.value,
            self.start_dt,
            self.due_dt,
            self.finished_dt,
            int(self.order or 0),
            self.details_html,
            bool(self.is_note),
            "; ".join(self.attachments) if self.attachments else "",
            bool(self.remind_at),
            bool(self.remind_10m),
            bool(self.remind_1h),
            bool(self.sent_at),
            bool(self.sent_10m),
            bool(self.sent_1h),
        ]

    @staticmethod
    def from_row(row_dict: dict) -> "DailyTask":
        status_str = (row_dict.get("Status") or "Unfinished").strip()
        try:
            status = TaskStatus(status_str)
        except Exception:
            s = status_str.lower()
            if s.startswith("work"):
                status = TaskStatus.WORKING
            elif s.startswith("fin"):
                status = TaskStatus.FINISHED
            elif s.startswith("post"):
                status = TaskStatus.POSTPONED
            else:
                status = TaskStatus.UNFINISHED

        attachments = (row_dict.get("Attachments") or "").strip()
        attach_list = [a.strip() for a in attachments.split(";") if a.strip()] if attachments else []

        start_dt = _parse_dt(row_dict.get("Start")) or datetime.now()
        due_dt = _parse_dt(row_dict.get("Due"))
        finished_dt = _parse_dt(row_dict.get("Finished"))

        try:
            order = int(row_dict.get("Order") or 0)
        except Exception:
            try:
                order = int(float(row_dict.get("Order") or 0))
            except Exception:
                order = 0

        t = DailyTask(
            id=str(row_dict.get("ID") or "").strip(),
            title=str(row_dict.get("Title") or "").strip(),
            status=status,
            start_dt=start_dt,
            due_dt=due_dt,
            finished_dt=finished_dt,
            order=order,
            details_html=str(row_dict.get("DetailsHtml") or ""),
            is_note=_parse_bool(row_dict.get("IsNote") or False),
            attachments=attach_list,
            remind_at=_parse_bool(row_dict.get("RemindAt")),
            remind_10m=_parse_bool(row_dict.get("Remind10m")),
            remind_1h=_parse_bool(row_dict.get("Remind1h")),
            sent_at=_parse_bool(row_dict.get("SentAt")),
            sent_10m=_parse_bool(row_dict.get("Sent10m")),
            sent_1h=_parse_bool(row_dict.get("Sent1h")),
        )
        t.mark_status(t.status)
        return t


@dataclass
class ProjectItem:
    """A lightweight project entry (for small tools/scripts)."""

    id: str
    title: str
    status: TaskStatus = TaskStatus.UNFINISHED
    category: str = "Coding"
    code_path: str = ""
    links: List[str] = field(default_factory=list)

    reminder_dt: Optional[datetime] = None
    order: int = 0

    details_html: str = ""
    updated_dt: datetime = field(default_factory=datetime.now)
    finished_dt: Optional[datetime] = None
    attachments: List[str] = field(default_factory=list)

    # Reminder settings
    remind_at: bool = False
    remind_10m: bool = False
    remind_1h: bool = False
    sent_at: bool = False
    sent_10m: bool = False
    sent_1h: bool = False

    def base_reminder_dt(self) -> Optional[datetime]:
        return self.reminder_dt

    def reset_reminder_sent_flags(self) -> None:
        self.sent_at = False
        self.sent_10m = False
        self.sent_1h = False

    def mark_status(self, new_status: TaskStatus, now: Optional[datetime] = None) -> None:
        now = now or datetime.now()
        self.updated_dt = now
        if new_status == TaskStatus.FINISHED:
            if self.finished_dt is None:
                self.finished_dt = now
        else:
            self.finished_dt = None
        self.status = new_status

    def to_row(self):
        return [
            self.id,
            self.title,
            self.status.value,
            self.category,
            self.code_path,
            "\n".join(self.links) if self.links else "",
            self.reminder_dt,
            self.updated_dt,
            self.finished_dt,
            int(self.order or 0),
            self.details_html,
            "; ".join(self.attachments) if self.attachments else "",
            bool(self.remind_at),
            bool(self.remind_10m),
            bool(self.remind_1h),
            bool(self.sent_at),
            bool(self.sent_10m),
            bool(self.sent_1h),
        ]

    @staticmethod
    def from_row(row_dict: dict) -> "ProjectItem":
        status_str = (row_dict.get("Status") or "Unfinished").strip()
        try:
            status = TaskStatus(status_str)
        except Exception:
            status = TaskStatus.UNFINISHED

        cat = str(row_dict.get("Category") or "").strip() or "Coding"

        links_raw = (row_dict.get("Links") or "").strip()
        links = [l.strip() for l in links_raw.splitlines() if l.strip()] if links_raw else []

        attachments = (row_dict.get("Attachments") or "").strip()
        attach_list = [a.strip() for a in attachments.split(";") if a.strip()] if attachments else []

        reminder_dt = _parse_dt(row_dict.get("Reminder"))
        updated_dt = _parse_dt(row_dict.get("Updated")) or datetime.now()
        finished_dt = _parse_dt(row_dict.get("Finished"))

        try:
            order = int(row_dict.get("Order") or 0)
        except Exception:
            try:
                order = int(float(row_dict.get("Order") or 0))
            except Exception:
                order = 0

        p = ProjectItem(
            id=str(row_dict.get("ID") or "").strip(),
            title=str(row_dict.get("Title") or "").strip(),
            status=status,
            code_path=str(row_dict.get("CodePath") or "").strip(),
            links=links,
            reminder_dt=reminder_dt,
            order=order,
            updated_dt=updated_dt,
            finished_dt=finished_dt,
            details_html=str(row_dict.get("DetailsHtml") or ""),
            attachments=attach_list,
            remind_at=_parse_bool(row_dict.get("RemindAt")),
            remind_10m=_parse_bool(row_dict.get("Remind10m")),
            remind_1h=_parse_bool(row_dict.get("Remind1h")),
            sent_at=_parse_bool(row_dict.get("SentAt")),
            sent_10m=_parse_bool(row_dict.get("Sent10m")),
            sent_1h=_parse_bool(row_dict.get("Sent1h")),
        )
        p.mark_status(p.status, now=updated_dt)
        return p
