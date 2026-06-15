from __future__ import annotations

import json
from datetime import datetime, timezone
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from standup_checker import cli
from standup_checker.models import StandupMessage


class CliTests(unittest.TestCase):
    def test_parse_args_loads_bot_token_from_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dotenv_path = temp_path / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "DISCORD_BOT_TOKEN=dotenv-token",
                        "ROSTER_FILE=roster.json",
                        "DISCORD_THREAD_ID=thread-1",
                        "TARGET_DATE=2026-06-13",
                        "COURSE_TIMEZONE=America/New_York",
                    ]
                ),
                encoding="utf-8",
            )
            previous_cwd = Path.cwd()
            with patch.dict(os.environ, {}, clear=True):
                try:
                    os.chdir(temp_path)
                    config = cli.parse_args([])
                finally:
                    os.chdir(previous_cwd)

        self.assertEqual(config.bot_token, "dotenv-token")
        self.assertEqual(config.roster_path, "roster.json")
        self.assertEqual(config.thread_id, "thread-1")

    def test_environment_overrides_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dotenv_path = temp_path / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "DISCORD_BOT_TOKEN=dotenv-token",
                        "ROSTER_FILE=roster.json",
                        "DISCORD_THREAD_ID=thread-1",
                        "TARGET_DATE=2026-06-13",
                        "COURSE_TIMEZONE=America/New_York",
                    ]
                ),
                encoding="utf-8",
            )
            previous_cwd = Path.cwd()
            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "env-token"}, clear=True):
                try:
                    os.chdir(temp_path)
                    config = cli.parse_args([])
                finally:
                    os.chdir(previous_cwd)

        self.assertEqual(config.bot_token, "env-token")

    def test_bot_token_flag_overrides_environment_and_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dotenv_path = temp_path / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "DISCORD_BOT_TOKEN=dotenv-token",
                        "ROSTER_FILE=roster.json",
                        "DISCORD_THREAD_ID=thread-1",
                        "TARGET_DATE=2026-06-13",
                        "COURSE_TIMEZONE=America/New_York",
                    ]
                ),
                encoding="utf-8",
            )
            previous_cwd = Path.cwd()
            with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "env-token"}, clear=True):
                try:
                    os.chdir(temp_path)
                    config = cli.parse_args(["--bot-token", "flag-token"])
                finally:
                    os.chdir(previous_cwd)

        self.assertEqual(config.bot_token, "flag-token")

    def test_direct_thread_id_does_not_require_team_config(self) -> None:
        config = cli.parse_args(
            [
                "--roster",
                "roster.json",
                "--thread-id",
                "thread-1",
                "--team-name",
                "team-1",
                "--target-date",
                "2026-06-13",
                "--timezone",
                "America/New_York",
                "--bot-token",
                "token",
            ]
        )

        self.assertEqual(config.thread_id, "thread-1")
        self.assertEqual(config.team_name, "team-1")

    def test_renders_json_report_with_direct_thread_id(self) -> None:
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
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            class FakeClient:
                def __init__(self, bot_token: str) -> None:
                    self.bot_token = bot_token

                def fetch_thread_messages(self, thread_id: str, start_at, end_at):
                    return [
                        StandupMessage(
                            message_id="m1",
                            author_id="100",
                            author_username="alice",
                            created_at=datetime(2026, 6, 13, 13, 0, tzinfo=timezone.utc),
                            content="Daily standup",
                            thread_id=thread_id,
                        )
                    ]

            stdout = io.StringIO()
            with patch.object(cli, "DiscordClient", FakeClient):
                with redirect_stdout(stdout):
                    exit_code = cli.main(
                        [
                            "--roster",
                            str(roster_path),
                            "--thread-id",
                            "thread-1",
                            "--target-date",
                            "2026-06-13",
                            "--timezone",
                            "America/New_York",
                            "--bot-token",
                            "token",
                            "--format",
                            "json",
                        ]
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["team_name"], "team-1")
        self.assertTrue(payload["records"][0]["present"])

    def test_renders_json_report_with_team_config(self) -> None:
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
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            team_config_path = Path(temp_dir) / "teams.json"
            team_config_path.write_text(
                json.dumps(
                    {
                        "teams": {
                            "team-1": {
                                "thread_id": "thread-from-config",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            class FakeClient:
                def __init__(self, bot_token: str) -> None:
                    self.bot_token = bot_token

                def fetch_thread_messages(self, thread_id: str, start_at, end_at):
                    return [
                        StandupMessage(
                            message_id="m1",
                            author_id="100",
                            author_username="alice",
                            created_at=datetime(2026, 6, 13, 13, 0, tzinfo=timezone.utc),
                            content="Daily standup",
                            thread_id=thread_id,
                        )
                    ]

            stdout = io.StringIO()
            with patch.object(cli, "DiscordClient", FakeClient):
                with redirect_stdout(stdout):
                    exit_code = cli.main(
                        [
                            "--roster",
                            str(roster_path),
                            "--team-name",
                            "team-1",
                            "--team-config",
                            str(team_config_path),
                            "--target-date",
                            "2026-06-13",
                            "--timezone",
                            "America/New_York",
                            "--bot-token",
                            "token",
                            "--format",
                            "json",
                        ]
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["thread_id"], "thread-from-config")
        self.assertEqual(payload["team_name"], "team-1")


if __name__ == "__main__":
    unittest.main()
