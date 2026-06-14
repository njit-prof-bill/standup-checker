from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class AppConfig:
    bot_token: str
    roster_path: str
    target_date: date
    timezone_name: str
    report_format: str
    thread_id: str | None = None
    team_name: str | None = None
    team_config_path: str | None = None

    @property
    def timezone(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {self.timezone_name}") from exc


def get_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
