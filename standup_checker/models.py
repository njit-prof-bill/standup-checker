from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class Student:
    student_id: str
    name: str
    discord_user_id: str | None = None
    discord_username: str | None = None


@dataclass(frozen=True)
class Team:
    team_id: str
    students: list[Student]


@dataclass(frozen=True)
class StandupMessage:
    message_id: str
    author_id: str | None
    author_username: str | None
    created_at: datetime
    content: str
    thread_id: str

    @property
    def content_preview(self) -> str:
        preview = " ".join(self.content.split())
        return preview[:80]


@dataclass(frozen=True)
class AttendanceRecord:
    student: Student
    present: bool
    messages: list[StandupMessage] = field(default_factory=list)


@dataclass(frozen=True)
class AttendanceReport:
    target_date: date
    timezone: str
    team_id: str
    thread_id: str
    records: list[AttendanceRecord]
    unmatched_messages: list[StandupMessage]
