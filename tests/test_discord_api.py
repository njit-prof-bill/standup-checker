from __future__ import annotations

import io
import json
import unittest
from urllib import error
from unittest.mock import patch

from standup_checker.discord_api import (
    DEFAULT_RATE_LIMIT_RETRY_SECONDS,
    RATE_LIMIT_SAFETY_BUFFER_SECONDS,
    DiscordClient,
    _parse_retry_after_seconds_from_body,
    _parse_retry_after_seconds_from_headers,
)


class DiscordClientRateLimitTests(unittest.TestCase):
    def test_fetch_retries_after_http_429_using_retry_after_from_body(self) -> None:
        sleep_calls: list[float] = []
        client = DiscordClient("token", sleep_fn=sleep_calls.append)
        rate_limited = self._http_error(
            body={"message": "rate limited", "retry_after": 1.5},
            headers={"Retry-After": "9"},
        )
        response = self._response(
            [
                {
                    "id": "m1",
                    "timestamp": "2026-06-13T14:00:00Z",
                    "content": "Daily standup",
                    "author": {"id": "100", "username": "alice"},
                }
            ]
        )

        with patch("standup_checker.discord_api.request.urlopen", side_effect=[rate_limited, response]):
            messages = client.fetch_thread_messages(
                thread_id="thread-1",
                start_at=self._timestamp("2026-06-13T00:00:00+00:00"),
                end_at=self._timestamp("2026-06-14T00:00:00+00:00"),
            )

        self.assertEqual([message.message_id for message in messages], ["m1"])
        self.assertEqual(sleep_calls, [1.5 + RATE_LIMIT_SAFETY_BUFFER_SECONDS])

    def test_retry_after_parsing_prefers_body_and_falls_back_to_header(self) -> None:
        self.assertEqual(
            _parse_retry_after_seconds_from_body('{"retry_after": "2.75"}'),
            2.75,
        )
        self.assertIsNone(_parse_retry_after_seconds_from_body("not-json"))
        self.assertEqual(
            _parse_retry_after_seconds_from_headers({"Retry-After": "3.5"}),
            3.5,
        )
        self.assertEqual(
            _parse_retry_after_seconds_from_headers({"retry-after": "4"}),
            4.0,
        )
        self.assertIsNone(_parse_retry_after_seconds_from_headers({}))

    def test_fetch_retries_after_http_429_using_retry_after_header_when_body_is_missing(self) -> None:
        sleep_calls: list[float] = []
        client = DiscordClient("token", sleep_fn=sleep_calls.append)
        rate_limited = self._http_error(body={"message": "rate limited"}, headers={"Retry-After": "2"})
        response = self._response([])

        with patch("standup_checker.discord_api.request.urlopen", side_effect=[rate_limited, response]):
            messages = client.fetch_thread_messages(
                thread_id="thread-1",
                start_at=self._timestamp("2026-06-13T00:00:00+00:00"),
                end_at=self._timestamp("2026-06-14T00:00:00+00:00"),
            )

        self.assertEqual(messages, [])
        self.assertEqual(sleep_calls, [2.0 + RATE_LIMIT_SAFETY_BUFFER_SECONDS])

    def test_fetch_retries_after_http_429_uses_default_delay_when_no_retry_after_is_present(self) -> None:
        sleep_calls: list[float] = []
        client = DiscordClient("token", sleep_fn=sleep_calls.append)
        rate_limited = self._http_error(body={"message": "rate limited"}, headers={})
        response = self._response([])

        with patch("standup_checker.discord_api.request.urlopen", side_effect=[rate_limited, response]):
            client.fetch_thread_messages(
                thread_id="thread-1",
                start_at=self._timestamp("2026-06-13T00:00:00+00:00"),
                end_at=self._timestamp("2026-06-14T00:00:00+00:00"),
            )

        self.assertEqual(
            sleep_calls,
            [DEFAULT_RATE_LIMIT_RETRY_SECONDS + RATE_LIMIT_SAFETY_BUFFER_SECONDS],
        )

    def _http_error(self, *, body: dict[str, object], headers: dict[str, str]) -> error.HTTPError:
        return error.HTTPError(
            url="https://discord.com/api/v10/channels/thread-1/messages?limit=100",
            code=429,
            msg="Too Many Requests",
            hdrs=headers,
            fp=io.BytesIO(json.dumps(body).encode("utf-8")),
        )

    def _response(self, payload: list[dict[str, object]]):
        class FakeResponse:
            def __init__(self, text: str) -> None:
                self.text = text

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def read(self) -> bytes:
                return self.text.encode("utf-8")

        return FakeResponse(json.dumps(payload))

    def _timestamp(self, value: str):
        from datetime import datetime

        return datetime.fromisoformat(value)


if __name__ == "__main__":
    unittest.main()
