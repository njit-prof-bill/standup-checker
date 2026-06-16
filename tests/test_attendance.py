from __future__ import annotations

from datetime import date, datetime, timezone
import json
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

from standup_checker import cli
from standup_checker.attendance import build_attendance_report
from standup_checker.discord_api import DiscordClient
from standup_checker.models import StandupMessage, Student, Team
from standup_checker.roster import load_team


class AttendanceReportTests(unittest.TestCase):
    def test_marks_present_and_absent_by_discord_username(self) -> None:
        team = Team(
            team_name="team-1",
            students=[
                Student(
                    student_id="s1",
                    student_name="Alice",
                    team_name="team-1",
                    discord_user_id="alice",
                ),
                Student(
                    student_id="s2",
                    student_name="Bob",
                    team_name="team-1",
                    discord_user_id="bob",
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
                author_username="robert",
                created_at=datetime(2026, 6, 13, 14, 0, tzinfo=timezone.utc),
                content="Looks like Bob by author id only.",
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
                                "discord_user_id": "alice",
                            },
                            {
                                "student_id": "s2",
                                "student_name": "Bob",
                                "team_name": "team-1",
                                "discord_user_id": "alice",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Duplicate discord_user_id"):
                load_team(str(roster_path))

    def test_roster_normalizes_discord_username_strings(self) -> None:
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
                                "discord_user_id": "  alice  ",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            team = load_team(str(roster_path))

        self.assertEqual(team.students[0].discord_user_id, "alice")

    def test_debug_output_lists_unmatched_usernames_when_message_author_differs(self) -> None:
        team = Team(
            team_name="team-1",
            students=[
                Student(
                    student_id="s1",
                    student_name="Alice",
                    team_name="team-1",
                    discord_user_id="alice",
                )
            ],
        )
        messages = [
            StandupMessage(
                message_id="m1",
                author_id="999",
                author_username="ronald",
                created_at=datetime(2026, 6, 13, 13, 0, tzinfo=timezone.utc),
                content="Daily standup",
                thread_id="thread-1",
            )
        ]
        report = build_attendance_report(
            team=team,
            thread_id="thread-1",
            target_date=date(2026, 6, 13),
            timezone=ZoneInfo("America/New_York"),
            messages=messages,
        )

        debug_output = cli.render_matching_debug(
            team=team,
            thread_id="thread-1",
            target_date=date(2026, 6, 13),
            timezone_name="America/New_York",
            start_local=datetime(2026, 6, 13, 0, 0, tzinfo=ZoneInfo("America/New_York")),
            end_local=datetime(2026, 6, 14, 0, 0, tzinfo=ZoneInfo("America/New_York")),
            messages=messages,
            report=report,
            fetch_stats=cli.MessageFetchStats(
                raw_message_count=1,
                filtered_message_count=1,
                raw_author_usernames=["ronald"],
                filtered_author_usernames=["ronald"],
            ),
        )

        self.assertIn("roster_discord_user_id_values: ['alice']", debug_output)
        self.assertIn("filtered_author_username_values: ['ronald x1']", debug_output)
        self.assertIn("matched_usernames: ['none']", debug_output)
        self.assertIn("unmatched_usernames: ['ronald']", debug_output)


class DiscordClientDateFilterTests(unittest.TestCase):
    def test_fetch_thread_messages_keeps_message_that_counts_for_new_york_date(self) -> None:
        class FakeDiscordClient(DiscordClient):
            def __init__(self) -> None:
                super().__init__("token")

            def _get_messages_page(self, thread_id: str, limit: int, before: str | None) -> list[dict]:
                if before is not None:
                    return []
                return [
                    {
                        "id": "m2",
                        "timestamp": "2026-06-14T04:30:00Z",
                        "content": "Too late for June 13 in New York",
                        "author": {"id": "100", "username": "alice"},
                    },
                    {
                        "id": "m1",
                        "timestamp": "2026-06-14T03:30:00Z",
                        "content": "Still June 13 in New York",
                        "author": {"id": "100", "username": "alice"},
                    },
                ]

        ny_tz = ZoneInfo("America/New_York")
        start_local = datetime(2026, 6, 13, 0, 0, tzinfo=ny_tz)
        end_local = datetime(2026, 6, 14, 0, 0, tzinfo=ny_tz)

        messages = FakeDiscordClient().fetch_thread_messages(
            thread_id="thread-1",
            start_at=start_local.astimezone(timezone.utc),
            end_at=end_local.astimezone(timezone.utc),
        )

        self.assertEqual([message.message_id for message in messages], ["m1"])


if __name__ == "__main__":
    unittest.main()
