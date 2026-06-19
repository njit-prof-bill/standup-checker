from __future__ import annotations

import csv
import json
from collections import defaultdict
from io import StringIO

from standup_checker.models import AttendanceReport, CourseAttendanceReport


def render_text_report(report: AttendanceReport) -> str:
    lines = [
        f"Attendance Report: {report.target_date.isoformat()}",
        f"Team: {report.team_name}",
        f"Thread: {report.thread_id}",
        f"Timezone: {report.timezone}",
        "",
        "Students:",
    ]

    for record in report.records:
        status = "present" if record.present else "absent"
        lines.append(
            f"- {record.student.student_name} ({record.student.student_id}): {status}"
        )
        for message in record.messages:
            lines.append(
                "  "
                f"* {message.created_at.isoformat()} "
                f"{message.author_username or message.author_id or 'unknown'} "
                f"[{message.message_id}] {message.content_preview}"
            )

    lines.append("")
    lines.append("Unmatched Messages:")
    if not report.unmatched_messages:
        lines.append("- none")
    else:
        for message in report.unmatched_messages:
            lines.append(
                "- "
                f"{message.created_at.isoformat()} "
                f"{message.author_username or message.author_id or 'unknown'} "
                f"[{message.message_id}] {message.content_preview}"
            )

    return "\n".join(lines)


def render_json_report(report: AttendanceReport) -> str:
    payload = _attendance_report_payload(report)
    return json.dumps(payload, indent=2)


def render_text_course_report(report: CourseAttendanceReport) -> str:
    counts = _course_report_counts(report)
    lines = [
        f"Course Attendance Report: {report.course}",
        f"Term: {report.term}",
        f"Timezone: {report.timezone}",
        f"Team Count: {counts['team_count']}",
        f"Date Count: {counts['date_count']}",
        f"Team-Date Count: {counts['team_date_count']}",
        f"Student Record Count: {counts['student_record_count']}",
        f"Present Count: {counts['present_count']}",
        f"Absent Count: {counts['absent_count']}",
        f"Unmatched Message Count: {counts['unmatched_message_count']}",
    ]

    reports_by_team: dict[str, list[AttendanceReport]] = defaultdict(list)
    for item in report.reports:
        reports_by_team[item.team_name].append(item)

    for team_name in sorted(reports_by_team):
        lines.append("")
        lines.append(f"Team: {team_name}")
        for team_report in sorted(reports_by_team[team_name], key=lambda item: item.target_date):
            lines.append("")
            lines.append(f"Date: {team_report.target_date.isoformat()}")
            lines.append(f"Thread: {team_report.thread_id}")
            lines.append("Students:")
            for record in team_report.records:
                status = "present" if record.present else "absent"
                lines.append(
                    f"- {record.student.student_name} ({record.student.student_id}): {status}"
                )
                for message in record.messages:
                    lines.append(
                        "  "
                        f"* {message.created_at.isoformat()} "
                        f"{message.author_username or message.author_id or 'unknown'} "
                        f"[{message.message_id}] {message.content_preview}"
                    )

            lines.append("")
            lines.append("Unmatched Messages:")
            if not team_report.unmatched_messages:
                lines.append("- none")
            else:
                for message in team_report.unmatched_messages:
                    lines.append(
                        "- "
                        f"{message.created_at.isoformat()} "
                        f"{message.author_username or message.author_id or 'unknown'} "
                        f"[{message.message_id}] {message.content_preview}"
                    )

    return "\n".join(lines)


def render_json_course_report(report: CourseAttendanceReport) -> str:
    counts = _course_report_counts(report)
    reports_by_team: dict[str, list[AttendanceReport]] = defaultdict(list)
    for item in report.reports:
        reports_by_team[item.team_name].append(item)

    payload = {
        "course": report.course,
        "term": report.term,
        "timezone": report.timezone,
        "summary": counts,
        "teams": [
            {
                "team_name": team_name,
                "reports": [
                    _attendance_report_payload(team_report)
                    for team_report in sorted(
                        reports_by_team[team_name],
                        key=lambda item: item.target_date,
                    )
                ],
            }
            for team_name in sorted(reports_by_team)
        ],
    }
    return json.dumps(payload, indent=2)


def render_csv_course_report(report: CourseAttendanceReport) -> str:
    dates = sorted({item.target_date for item in report.reports})
    attendance_by_student: dict[tuple[str, str, str], dict] = {}

    for team_report in report.reports:
        for record in team_report.records:
            key = (
                record.student.student_name,
                record.student.student_id,
                record.student.team_name,
            )
            student_row = attendance_by_student.setdefault(
                key,
                {
                    "student_name": record.student.student_name,
                    "student_id": record.student.student_id,
                    "team": record.student.team_name,
                    "attendance": {},
                },
            )
            student_row["attendance"][team_report.target_date] = 1 if record.present else 0

    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["student_name", "student_id", "team", *[item.isoformat() for item in dates]])

    for key in sorted(attendance_by_student, key=lambda item: item[0]):
        row = attendance_by_student[key]
        writer.writerow(
            [
                row["student_name"],
                row["student_id"],
                row["team"],
                *[row["attendance"].get(item, 0) for item in dates],
            ]
        )

    return output.getvalue()


def _attendance_report_payload(report: AttendanceReport) -> dict:
    return {
        "target_date": report.target_date.isoformat(),
        "timezone": report.timezone,
        "team_name": report.team_name,
        "thread_id": report.thread_id,
        "records": [
            {
                "student_id": record.student.student_id,
                "student_name": record.student.student_name,
                "team_name": record.student.team_name,
                "present": record.present,
                "messages": [
                    {
                        "message_id": message.message_id,
                        "author_id": message.author_id,
                        "author_username": message.author_username,
                        "timestamp": message.created_at.isoformat(),
                        "content_preview": message.content_preview,
                    }
                    for message in record.messages
                ],
            }
            for record in report.records
        ],
        "unmatched_messages": [
            {
                "message_id": message.message_id,
                "author_id": message.author_id,
                "author_username": message.author_username,
                "timestamp": message.created_at.isoformat(),
                "content_preview": message.content_preview,
            }
            for message in report.unmatched_messages
        ],
    }


def _course_report_counts(report: CourseAttendanceReport) -> dict[str, int]:
    team_names = {item.team_name for item in report.reports}
    dates = {item.target_date for item in report.reports}
    student_record_count = sum(len(item.records) for item in report.reports)
    present_count = sum(
        1
        for item in report.reports
        for record in item.records
        if record.present
    )
    absent_count = student_record_count - present_count
    unmatched_message_count = sum(len(item.unmatched_messages) for item in report.reports)
    return {
        "team_count": len(team_names),
        "date_count": len(dates),
        "team_date_count": len(report.reports),
        "student_record_count": student_record_count,
        "present_count": present_count,
        "absent_count": absent_count,
        "unmatched_message_count": unmatched_message_count,
    }
