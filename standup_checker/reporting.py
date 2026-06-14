from __future__ import annotations

import json

from standup_checker.models import AttendanceReport


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
    payload = {
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
    return json.dumps(payload, indent=2)
