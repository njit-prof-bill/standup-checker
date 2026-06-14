from __future__ import annotations

import json
from datetime import datetime, timezone
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from standup_checker import cli
from standup_checker.models import StandupMessage


class CliTests(unittest.TestCase):
    def test_renders_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            roster_path = Path(temp_dir) / "roster.json"
            roster_path.write_text(
                json.dumps(
                    {
                        "team_id": "team-1",
                        "students": [
                            {
                                "student_id": "s1",
                                "name": "Alice",
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
        self.assertEqual(payload["team_id"], "team-1")
        self.assertTrue(payload["records"][0]["present"])


if __name__ == "__main__":
    unittest.main()
