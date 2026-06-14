from __future__ import annotations

import json
from pathlib import Path

from standup_checker.models import Student, Team


def load_team(roster_path: str) -> Team:
    path = Path(roster_path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    team_id = payload.get("team_id")
    students_payload = payload.get("students")
    if not team_id or not isinstance(students_payload, list):
        raise ValueError("Roster file must contain team_id and students.")

    students: list[Student] = []
    for item in students_payload:
        student_id = item.get("student_id")
        name = item.get("name")
        if not student_id or not name:
            raise ValueError("Each student must contain student_id and name.")
        students.append(
            Student(
                student_id=str(student_id),
                name=str(name),
                discord_user_id=_optional_string(item.get("discord_user_id")),
                discord_username=_normalize_username(item.get("discord_username")),
            )
        )

    return Team(team_id=str(team_id), students=students)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_username(value: object) -> str | None:
    text = _optional_string(value)
    if text is None:
        return None
    return text.casefold()
