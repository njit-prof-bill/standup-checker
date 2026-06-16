from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path: Path, override: bool = False) -> None:
        try:
            lines = dotenv_path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            if not key:
                continue

            if not override and key in os.environ:
                continue

            os.environ[key] = value.strip()


@dataclass(frozen=True)
class AppConfig:
    bot_token: str
    roster_path: str
    target_date: date
    timezone_name: str
    report_format: str
    debug_matching: bool = False
    thread_id: str | None = None
    team_name: str | None = None
    team_config_path: str | None = None

    @property
    def timezone(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {self.timezone_name}") from exc


def load_project_dotenv() -> None:
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


def get_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
