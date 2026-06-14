from __future__ import annotations

import json
from pathlib import Path

from standup_checker.models import Student, Team


def load_team(roster_path: str) -> Team:
    path = Path(roster_path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    students_payload = payload.get("students")
    if not isinstance(students_payload, list) or not students_payload:
        raise ValueError("Roster file must contain a non-empty students list.")

    students: list[Student] = []
    team_name: str | None = None
    for item in students_payload:
        student_id = item.get("student_id")
        student_name = item.get("student_name")
        item_team_name = item.get("team_name")
        discord_user_id = _optional_string(item.get("discord_user_id"))
        if not student_id or not student_name or not item_team_name or not discord_user_id:
            raise ValueError(
                "Each student must contain student_id, student_name, team_name, and discord_user_id."
            )
        normalized_team_name = str(item_team_name).strip()
        if team_name is None:
            team_name = normalized_team_name
        elif team_name != normalized_team_name:
            raise ValueError("Roster file must contain students for exactly one team.")
        students.append(
            Student(
                student_id=str(student_id),
                student_name=str(student_name),
                team_name=normalized_team_name,
                discord_user_id=discord_user_id,
                discord_display_name=_normalize_display_name(item.get("discord_display_name")),
            )
        )

    return Team(team_name=team_name, students=students)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_display_name(value: object) -> str | None:
    return _optional_string(value)
