from __future__ import annotations

import json
from datetime import datetime
from urllib import error, parse, request

from standup_checker.models import MessageFetchStats, StandupMessage


DISCORD_API_BASE_URL = "https://discord.com/api/v10"


class DiscordClient:
    def __init__(self, bot_token: str, base_url: str = DISCORD_API_BASE_URL) -> None:
        self.bot_token = bot_token
        self.base_url = base_url.rstrip("/")

    def fetch_thread_messages(
        self,
        thread_id: str,
        start_at: datetime,
        end_at: datetime,
        debug_stats: MessageFetchStats | None = None,
    ) -> list[StandupMessage]:
        messages: list[StandupMessage] = []
        before: str | None = None
        raw_message_count = 0
        raw_author_usernames: list[str] = []

        while True:
            page = self._get_messages_page(thread_id=thread_id, limit=100, before=before)
            if not page:
                break

            normalized_page = [normalize_message(item, thread_id) for item in page]
            raw_message_count += len(normalized_page)
            raw_author_usernames.extend(
                message.author_username
                for message in normalized_page
                if message.author_username is not None
            )
            messages.extend(
                message
                for message in normalized_page
                if start_at <= message.created_at < end_at
            )

            oldest_message = normalized_page[-1]
            if oldest_message.created_at < start_at or len(page) < 100:
                break

            before = oldest_message.message_id

        messages.sort(key=lambda item: item.created_at)
        if debug_stats is not None:
            debug_stats.raw_message_count = raw_message_count
            debug_stats.filtered_message_count = len(messages)
            debug_stats.raw_author_usernames = raw_author_usernames
            debug_stats.filtered_author_usernames = [
                message.author_username
                for message in messages
                if message.author_username is not None
            ]
        return messages

    def _get_messages_page(
        self,
        thread_id: str,
        limit: int,
        before: str | None,
    ) -> list[dict]:
        query = {"limit": str(limit)}
        if before is not None:
            query["before"] = before

        url = (
            f"{self.base_url}/channels/{thread_id}/messages?"
            f"{parse.urlencode(query)}"
        )
        req = request.Request(
            url,
            headers={
                "Authorization": f"Bot {self.bot_token}",
                "User-Agent": "standup-checker/0.1",
            },
        )
        try:
            with request.urlopen(req) as response:
                payload = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Discord API request failed with status {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Discord API request failed: {exc.reason}") from exc

        data = json.loads(payload)
        if not isinstance(data, list):
            raise RuntimeError("Discord API response was not a message list.")
        return data


def normalize_message(payload: dict, thread_id: str) -> StandupMessage:
    author = payload.get("author") or {}
    return StandupMessage(
        message_id=str(payload["id"]),
        author_id=_optional_string(author.get("id")),
        author_username=_normalize_username(author),
        created_at=_parse_timestamp(payload["timestamp"]),
        content=str(payload.get("content", "")),
        thread_id=thread_id,
    )


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_username(author: dict) -> str | None:
    username = _optional_string(author.get("username"))
    if username is None:
        return None
    return username.casefold()
