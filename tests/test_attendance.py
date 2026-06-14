from __future__ import annotations

from datetime import date, datetime, timezone
import json
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

from standup_checker.attendance import build_attendance_report
from standup_checker.models import StandupMessage, Student, Team
from standup_checker.roster import load_team


class AttendanceReportTests(unittest.TestCase):
    def test_marks_present_and_absent_by_discord_user_id(self) -> None:
        team = Team(
            team_name="team-1",
            students=[
                Student(
                    student_id="s1",
                    student_name="Alice",
                    team_name="team-1",
                    discord_user_id="100",
                ),
                Student(
                    student_id="s2",
                    student_name="Bob",
                    team_name="team-1",
                    discord_user_id="200",
                    discord_display_name="bob",
                ),
            ],
        )
        messages = [
            StandupMessage(
                message_id="m1",
                author_id="100",
                author_username="alice",
                created_at=datetime(2026, 6, 13, 13, 0, tzinfo=timezone.utc),
                content="Yesterday I finished the draft.",
                thread_id="thread-1",
            ),
            StandupMessage(
                message_id="m2",
                author_id="999",
                author_username="bob",
                created_at=datetime(2026, 6, 13, 14, 0, tzinfo=timezone.utc),
                content="Looks like Bob by display name only.",
                thread_id="thread-1",
            ),
        ]

        report = build_attendance_report(
            team=team,
            thread_id="thread-1",
            target_date=date(2026, 6, 13),
            timezone=ZoneInfo("America/New_York"),
            messages=messages,
        )

        self.assertEqual([record.present for record in report.records], [True, False])
        self.assertEqual(report.records[0].messages, [messages[0]])
        self.assertEqual(report.unmatched_messages, [messages[1]])

    def test_roster_rejects_duplicate_discord_user_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            roster_path = Path(temp_dir) / "roster.json"
            roster_path.write_text(
                json.dumps(
                    {
                        "students": [
                            {
                                "student_id": "s1",
                                "student_name": "Alice",
                                "team_name": "team-1",
                                "discord_user_id": "100",
                            },
                            {
                                "student_id": "s2",
                                "student_name": "Bob",
                                "team_name": "team-1",
                                "discord_user_id": "100",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Duplicate discord_user_id"):
                load_team(str(roster_path))


if __name__ == "__main__":
    unittest.main()
