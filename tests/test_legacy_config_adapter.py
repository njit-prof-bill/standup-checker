from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from standup_checker.legacy_config_adapter import (
    LEGACY_COMPAT_COURSE,
    LEGACY_COMPAT_TERM,
    adapt_legacy_inputs_to_course_config,
)


class LegacyConfigAdapterTests(unittest.TestCase):
    def test_adapts_direct_thread_inputs_to_canonical_course_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            roster_path = self._write_roster(
                Path(temp_dir) / "roster.json",
                team_name="team-1",
                discord_user_id="  alice  ",
            )

            config = adapt_legacy_inputs_to_course_config(
                roster_path=str(roster_path),
                thread_id="thread-1",
                team_name=None,
                team_config_path=None,
                target_date=date(2026, 6, 13),
                timezone_name="America/New_York",
            )

        self.assertEqual(config.course, LEGACY_COMPAT_COURSE)
        self.assertEqual(config.term, LEGACY_COMPAT_TERM)
        self.assertEqual(config.timezone, "America/New_York")
        self.assertEqual(config.dates, [date(2026, 6, 13)])
        self.assertEqual(len(config.teams), 1)
        self.assertEqual(config.teams[0].team_name, "team-1")
        self.assertEqual(config.teams[0].thread_id, "thread-1")
        self.assertEqual(config.teams[0].students[0].team_name, "team-1")
        self.assertEqual(config.teams[0].students[0].discord_user_id, "alice")

    def test_adapts_team_config_inputs_to_canonical_course_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            roster_path = self._write_roster(temp_path / "roster.json", team_name="team-1")
            team_config_path = temp_path / "teams.json"
            team_config_path.write_text(
                json.dumps({"teams": {"team-1": {"thread_id": "thread-from-config"}}}),
                encoding="utf-8",
            )

            config = adapt_legacy_inputs_to_course_config(
                roster_path=str(roster_path),
                thread_id=None,
                team_name="team-1",
                team_config_path=str(team_config_path),
                target_date=date(2026, 6, 13),
                timezone_name="America/New_York",
            )

        self.assertEqual(config.teams[0].thread_id, "thread-from-config")
        self.assertEqual(config.teams[0].students[0].discord_user_id, "alice")

    def test_rejects_team_name_mismatch_using_current_cli_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            roster_path = self._write_roster(Path(temp_dir) / "roster.json", team_name="team-1")

            with self.assertRaisesRegex(ValueError, "Roster team 'team-1' does not match"):
                adapt_legacy_inputs_to_course_config(
                    roster_path=str(roster_path),
                    thread_id="thread-1",
                    team_name="other-team",
                    team_config_path=None,
                    target_date=date(2026, 6, 13),
                    timezone_name="America/New_York",
                )

    def _write_roster(
        self,
        path: Path,
        *,
        team_name: str,
        discord_user_id: str = "alice",
    ) -> Path:
        path.write_text(
            json.dumps(
                {
                    "students": [
                        {
                            "student_id": "s1",
                            "student_name": "Alice",
                            "team_name": team_name,
                            "discord_user_id": discord_user_id,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return path


if __name__ == "__main__":
    unittest.main()
