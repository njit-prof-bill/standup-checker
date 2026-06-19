from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timezone

from standup_checker.models import (
    AttendanceRecord,
    AttendanceReport,
    CourseAttendanceReport,
    StandupMessage,
    Student,
)
from standup_checker.reporting import (
    render_csv_course_report,
    render_json_course_report,
    render_text_course_report,
)


class CourseAttendanceReportingTests(unittest.TestCase):
    def test_render_json_course_report_groups_by_team_and_includes_summary(self) -> None:
        aggregate = CourseAttendanceReport(
            course="CS 490",
            term="Summer 2026",
            timezone="America/New_York",
            reports=[
                self._attendance_report(
                    team_name="team-b",
                    thread_id="thread-b",
                    target_date=date(2026, 6, 14),
                    records=[
                        self._record("s2", "Bob", "team-b", present=False),
                    ],
                    unmatched_messages=[],
                ),
                self._attendance_report(
                    team_name="team-a",
                    thread_id="thread-a",
                    target_date=date(2026, 6, 13),
                    records=[
                        self._record(
                            "s1",
                            "Alice",
                            "team-a",
                            present=True,
                            messages=[
                                self._message(
                                    "m1",
                                    "alice",
                                    "thread-a",
                                    "2026-06-13T14:00:00+00:00",
                                )
                            ],
                        )
                    ],
                    unmatched_messages=[
                        self._message(
                            "m2",
                            "intruder",
                            "thread-a",
                            "2026-06-13T15:00:00+00:00",
                        )
                    ],
                ),
                self._attendance_report(
                    team_name="team-a",
                    thread_id="thread-a",
                    target_date=date(2026, 6, 14),
                    records=[
                        self._record("s1", "Alice", "team-a", present=False),
                    ],
                    unmatched_messages=[],
                ),
            ],
        )

        payload = json.loads(render_json_course_report(aggregate))

        self.assertEqual(payload["course"], "CS 490")
        self.assertEqual(payload["term"], "Summer 2026")
        self.assertEqual(payload["timezone"], "America/New_York")
        self.assertEqual(
            payload["summary"],
            {
                "team_count": 2,
                "date_count": 2,
                "team_date_count": 3,
                "student_record_count": 3,
                "present_count": 1,
                "absent_count": 2,
                "unmatched_message_count": 1,
            },
        )
        self.assertEqual([team["team_name"] for team in payload["teams"]], ["team-a", "team-b"])
        self.assertEqual(
            [report["target_date"] for report in payload["teams"][0]["reports"]],
            ["2026-06-13", "2026-06-14"],
        )
        self.assertEqual(payload["teams"][0]["reports"][0]["unmatched_messages"][0]["message_id"], "m2")
        self.assertTrue(payload["teams"][0]["reports"][0]["records"][0]["present"])
        self.assertFalse(payload["teams"][1]["reports"][0]["records"][0]["present"])

    def test_render_text_course_report_groups_by_team_then_date_and_includes_summary(self) -> None:
        aggregate = CourseAttendanceReport(
            course="CS 490",
            term="Summer 2026",
            timezone="America/New_York",
            reports=[
                self._attendance_report(
                    team_name="team-b",
                    thread_id="thread-b",
                    target_date=date(2026, 6, 14),
                    records=[
                        self._record("s2", "Bob", "team-b", present=False),
                    ],
                    unmatched_messages=[],
                ),
                self._attendance_report(
                    team_name="team-a",
                    thread_id="thread-a",
                    target_date=date(2026, 6, 13),
                    records=[
                        self._record(
                            "s1",
                            "Alice",
                            "team-a",
                            present=True,
                            messages=[
                                self._message(
                                    "m1",
                                    "alice",
                                    "thread-a",
                                    "2026-06-13T14:00:00+00:00",
                                )
                            ],
                        )
                    ],
                    unmatched_messages=[
                        self._message(
                            "m2",
                            "intruder",
                            "thread-a",
                            "2026-06-13T15:00:00+00:00",
                        )
                    ],
                ),
                self._attendance_report(
                    team_name="team-a",
                    thread_id="thread-a",
                    target_date=date(2026, 6, 14),
                    records=[
                        self._record("s1", "Alice", "team-a", present=False),
                    ],
                    unmatched_messages=[],
                ),
            ],
        )

        text = render_text_course_report(aggregate)

        self.assertIn("Course Attendance Report: CS 490", text)
        self.assertIn("Team Count: 2", text)
        self.assertIn("Date Count: 2", text)
        self.assertIn("Team-Date Count: 3", text)
        self.assertIn("Student Record Count: 3", text)
        self.assertIn("Present Count: 1", text)
        self.assertIn("Absent Count: 2", text)
        self.assertIn("Unmatched Message Count: 1", text)
        self.assertLess(text.index("Team: team-a"), text.index("Team: team-b"))
        self.assertLess(text.index("Date: 2026-06-13"), text.index("Date: 2026-06-14"))
        self.assertIn("- Alice (s1): present", text)
        self.assertIn("- Alice (s1): absent", text)
        self.assertIn("intruder [m2] Daily standup update", text)
        self.assertIn("Unmatched Messages:\n- none", text)

    def test_render_csv_course_report_builds_student_date_matrix_sorted_by_name(self) -> None:
        aggregate = CourseAttendanceReport(
            course="CS 490",
            term="Summer 2026",
            timezone="America/New_York",
            reports=[
                self._attendance_report(
                    team_name="team-b",
                    thread_id="thread-b",
                    target_date=date(2026, 6, 14),
                    records=[self._record("s2", "Bob", "team-b", present=False)],
                    unmatched_messages=[],
                ),
                self._attendance_report(
                    team_name="team-a",
                    thread_id="thread-a",
                    target_date=date(2026, 6, 13),
                    records=[
                        self._record("s1", "Alice", "team-a", present=True),
                        self._record("s3", "Charlie", "team-a", present=False),
                    ],
                    unmatched_messages=[],
                ),
                self._attendance_report(
                    team_name="team-a",
                    thread_id="thread-a",
                    target_date=date(2026, 6, 14),
                    records=[
                        self._record("s1", "Alice", "team-a", present=False),
                        self._record("s3", "Charlie", "team-a", present=True),
                    ],
                    unmatched_messages=[],
                ),
                self._attendance_report(
                    team_name="team-b",
                    thread_id="thread-b",
                    target_date=date(2026, 6, 13),
                    records=[self._record("s2", "Bob", "team-b", present=True)],
                    unmatched_messages=[],
                ),
            ],
        )

        csv_text = render_csv_course_report(aggregate)

        self.assertEqual(
            csv_text,
            "\n".join(
                [
                    "student_name,student_id,team,2026-06-13,2026-06-14",
                    "Alice,s1,team-a,1,0",
                    "Bob,s2,team-b,1,0",
                    "Charlie,s3,team-a,0,1",
                    "",
                ]
            ),
        )

    def _attendance_report(
        self,
        *,
        team_name: str,
        thread_id: str,
        target_date: date,
        records: list[AttendanceRecord],
        unmatched_messages: list[StandupMessage],
    ) -> AttendanceReport:
        return AttendanceReport(
            target_date=target_date,
            timezone="America/New_York",
            team_name=team_name,
            thread_id=thread_id,
            records=records,
            unmatched_messages=unmatched_messages,
        )

    def _record(
        self,
        student_id: str,
        student_name: str,
        team_name: str,
        *,
        present: bool,
        messages: list[StandupMessage] | None = None,
    ) -> AttendanceRecord:
        return AttendanceRecord(
            student=Student(
                student_id=student_id,
                student_name=student_name,
                team_name=team_name,
                discord_user_id=student_name.casefold(),
            ),
            present=present,
            messages=messages or [],
        )

    def _message(
        self,
        message_id: str,
        author_username: str,
        thread_id: str,
        created_at_iso: str,
    ) -> StandupMessage:
        return StandupMessage(
            message_id=message_id,
            author_id="100",
            author_username=author_username,
            created_at=datetime.fromisoformat(created_at_iso),
            content="Daily standup update",
            thread_id=thread_id,
        )


if __name__ == "__main__":
    unittest.main()
