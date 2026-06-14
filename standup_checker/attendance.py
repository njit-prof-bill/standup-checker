from __future__ import annotations

from collections import defaultdict
from datetime import date
from zoneinfo import ZoneInfo

from standup_checker.models import AttendanceRecord, AttendanceReport, StandupMessage, Team


def build_attendance_report(
    *,
    team: Team,
    thread_id: str,
    target_date: date,
    timezone: ZoneInfo,
    messages: list[StandupMessage],
) -> AttendanceReport:
    students_by_user_id = {
        student.discord_user_id: student
        for student in team.students
        if student.discord_user_id
    }

    matched_messages: dict[str, list[StandupMessage]] = defaultdict(list)
    unmatched_messages: list[StandupMessage] = []

    for message in messages:
        student = None
        if message.author_id is not None:
            student = students_by_user_id.get(message.author_id)

        if student is None:
            unmatched_messages.append(message)
            continue

        matched_messages[student.student_id].append(message)

    records = [
        AttendanceRecord(
            student=student,
            present=bool(matched_messages.get(student.student_id)),
            messages=matched_messages.get(student.student_id, []),
        )
        for student in team.students
    ]

    return AttendanceReport(
        target_date=target_date,
        timezone=str(timezone.key),
        team_name=team.team_name,
        thread_id=thread_id,
        records=records,
        unmatched_messages=unmatched_messages,
    )
