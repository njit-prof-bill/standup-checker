from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from standup_checker.roster import load_course_config


class CourseConfigLoaderTests(unittest.TestCase):
    def test_loads_valid_course_config(self) -> None:
        payload = {
            "course": "CS 490",
            "term": "Summer 2026",
            "timezone": "America/New_York",
            "dates": ["2026-06-12", "2026-06-13"],
            "teams": [
                {
                    "team_name": "breeze",
                    "thread_id": "1509994039754231828",
                    "students": [
                        {
                            "student_id": "Ramirezzz1",
                            "student_name": "Ramirez, Ronald Esgardo",
                            "discord_user_id": "ronald",
                        }
                    ],
                }
            ],
        }

        config = self._load_payload(payload)

        self.assertEqual(config.course, "CS 490")
        self.assertEqual(config.term, "Summer 2026")
        self.assertEqual(config.timezone, "America/New_York")
        self.assertEqual([item.isoformat() for item in config.dates], ["2026-06-12", "2026-06-13"])
        self.assertEqual(len(config.teams), 1)
        self.assertEqual(config.teams[0].team_name, "breeze")
        self.assertEqual(config.teams[0].thread_id, "1509994039754231828")
        self.assertEqual(config.teams[0].students[0].team_name, "breeze")
        self.assertEqual(config.teams[0].students[0].discord_user_id, "ronald")

    def test_rejects_empty_dates(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty dates list"):
            self._load_payload(
                {
                    "course": "CS 490",
                    "term": "Summer 2026",
                    "timezone": "America/New_York",
                    "dates": [],
                    "teams": [self._team_payload()],
                }
            )

    def test_rejects_invalid_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid date in course config"):
            self._load_payload(
                {
                    "course": "CS 490",
                    "term": "Summer 2026",
                    "timezone": "America/New_York",
                    "dates": ["2026-13-40"],
                    "teams": [self._team_payload()],
                }
            )

    def test_rejects_empty_teams(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty teams list"):
            self._load_payload(
                {
                    "course": "CS 490",
                    "term": "Summer 2026",
                    "timezone": "America/New_York",
                    "dates": ["2026-06-12"],
                    "teams": [],
                }
            )

    def test_rejects_missing_team_name(self) -> None:
        team = self._team_payload()
        del team["team_name"]

        with self.assertRaisesRegex(ValueError, "team_name"):
            self._load_payload(self._base_payload_with_team(team))

    def test_rejects_missing_thread_id(self) -> None:
        team = self._team_payload()
        del team["thread_id"]

        with self.assertRaisesRegex(ValueError, "thread_id"):
            self._load_payload(self._base_payload_with_team(team))

    def test_rejects_missing_students(self) -> None:
        team = self._team_payload()
        del team["students"]

        with self.assertRaisesRegex(ValueError, "students list"):
            self._load_payload(self._base_payload_with_team(team))

    def test_rejects_duplicate_team_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate team_name"):
            self._load_payload(
                {
                    "course": "CS 490",
                    "term": "Summer 2026",
                    "timezone": "America/New_York",
                    "dates": ["2026-06-12"],
                    "teams": [self._team_payload(), self._team_payload()],
                }
            )

    def test_rejects_duplicate_student_id_within_team(self) -> None:
        team = self._team_payload()
        team["students"] = [
            {
                "student_id": "s1",
                "student_name": "Alice",
                "discord_user_id": "alice",
            },
            {
                "student_id": "s1",
                "student_name": "Bob",
                "discord_user_id": "bob",
            },
        ]

        with self.assertRaisesRegex(ValueError, "Duplicate student_id"):
            self._load_payload(self._base_payload_with_team(team))

    def test_rejects_duplicate_discord_user_id_within_team(self) -> None:
        team = self._team_payload()
        team["students"] = [
            {
                "student_id": "s1",
                "student_name": "Alice",
                "discord_user_id": "alice",
            },
            {
                "student_id": "s2",
                "student_name": "Bob",
                "discord_user_id": "alice",
            },
        ]

        with self.assertRaisesRegex(ValueError, "Duplicate discord_user_id"):
            self._load_payload(self._base_payload_with_team(team))

    def _load_payload(self, payload: dict) -> object:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "course-config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_course_config(str(path))

    def _base_payload_with_team(self, team: dict) -> dict:
        return {
            "course": "CS 490",
            "term": "Summer 2026",
            "timezone": "America/New_York",
            "dates": ["2026-06-12"],
            "teams": [team],
        }

    def _team_payload(self) -> dict:
        return {
            "team_name": "breeze",
            "thread_id": "1509994039754231828",
            "students": [
                {
                    "student_id": "Ramirezzz1",
                    "student_name": "Ramirez, Ronald Esgardo",
                    "discord_user_id": "ronald",
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
