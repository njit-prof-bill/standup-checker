from __future__ import annotations

import json
from datetime import date
from json import JSONDecodeError
from pathlib import Path

from standup_checker.models import CourseConfig, CourseTeam, Student, Team


def load_team(roster_path: str) -> Team:
    path = Path(roster_path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Roster file not found: {roster_path}") from exc
    except JSONDecodeError as exc:
        raise ValueError(f"Roster file is not valid JSON: {roster_path}") from exc

    students_payload = payload.get("students")
    if not isinstance(students_payload, list) or not students_payload:
        raise ValueError("Roster file must contain a non-empty students list.")

    students: list[Student] = []
    team_name: str | None = None
    seen_student_ids: set[str] = set()
    seen_discord_user_ids: set[str] = set()
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
        normalized_student_id = str(student_id)
        if normalized_student_id in seen_student_ids:
            raise ValueError(f"Duplicate student_id in roster: {normalized_student_id}")
        if discord_user_id in seen_discord_user_ids:
            raise ValueError(f"Duplicate discord_user_id in roster: {discord_user_id}")
        seen_student_ids.add(normalized_student_id)
        seen_discord_user_ids.add(discord_user_id)
        students.append(
            Student(
                student_id=normalized_student_id,
                student_name=str(student_name),
                team_name=normalized_team_name,
                discord_user_id=discord_user_id,
                discord_display_name=_normalize_display_name(item.get("discord_display_name")),
            )
        )

    return Team(team_name=team_name, students=students)


def load_course_config(config_path: str) -> CourseConfig:
    payload = _load_json_file(config_path)

    course = _required_string(payload.get("course"), "course")
    term = _required_string(payload.get("term"), "term")
    timezone = _required_string(payload.get("timezone"), "timezone")

    dates_payload = payload.get("dates")
    if not isinstance(dates_payload, list) or not dates_payload:
        raise ValueError("Course config must contain a non-empty dates list.")
    dates = [_parse_date(item) for item in dates_payload]

    teams_payload = payload.get("teams")
    if not isinstance(teams_payload, list) or not teams_payload:
        raise ValueError("Course config must contain a non-empty teams list.")

    teams: list[CourseTeam] = []
    seen_team_names: set[str] = set()
    for item in teams_payload:
        if not isinstance(item, dict):
            raise ValueError("Each team entry in course config must be an object.")

        team_name = _required_string(item.get("team_name"), "team_name")
        if team_name in seen_team_names:
            raise ValueError(f"Duplicate team_name in course config: {team_name}")
        seen_team_names.add(team_name)

        thread_id = _required_string(item.get("thread_id"), "thread_id")
        students_payload = item.get("students")
        if not isinstance(students_payload, list) or not students_payload:
            raise ValueError(
                f"Team '{team_name}' in course config must contain a non-empty students list."
            )

        students = _load_students_for_team(
            students_payload=students_payload,
            team_name=team_name,
        )
        teams.append(
            CourseTeam(
                team_name=team_name,
                thread_id=thread_id,
                students=students,
            )
        )

    return CourseConfig(
        course=course,
        term=term,
        timezone=timezone,
        dates=dates,
        teams=teams,
    )


def _load_json_file(path_text: str) -> dict:
    path = Path(path_text)
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Roster file not found: {path_text}") from exc
    except JSONDecodeError as exc:
        raise ValueError(f"Roster file is not valid JSON: {path_text}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Top-level JSON payload must be an object.")
    return payload


def _load_students_for_team(
    *,
    students_payload: list,
    team_name: str,
) -> list[Student]:
    students: list[Student] = []
    seen_student_ids: set[str] = set()
    seen_discord_user_ids: set[str] = set()

    for item in students_payload:
        if not isinstance(item, dict):
            raise ValueError(f"Each student in team '{team_name}' must be an object.")

        student_id = item.get("student_id")
        student_name = item.get("student_name")
        discord_user_id = _optional_string(item.get("discord_user_id"))
        if not student_id or not student_name or not discord_user_id:
            raise ValueError(
                f"Each student in team '{team_name}' must contain student_id, student_name, and discord_user_id."
            )

        normalized_student_id = str(student_id).strip()
        if normalized_student_id in seen_student_ids:
            raise ValueError(
                f"Duplicate student_id in team '{team_name}': {normalized_student_id}"
            )
        if discord_user_id in seen_discord_user_ids:
            raise ValueError(
                f"Duplicate discord_user_id in team '{team_name}': {discord_user_id}"
            )

        seen_student_ids.add(normalized_student_id)
        seen_discord_user_ids.add(discord_user_id)
        students.append(
            Student(
                student_id=normalized_student_id,
                student_name=str(student_name).strip(),
                team_name=team_name,
                discord_user_id=discord_user_id,
                discord_display_name=_normalize_display_name(item.get("discord_display_name")),
            )
        )

    return students


def _required_string(value: object, field_name: str) -> str:
    text = _optional_string(value)
    if text is None:
        raise ValueError(f"Course config is missing required field: {field_name}")
    return text


def _parse_date(value: object) -> date:
    text = _optional_string(value)
    if text is None:
        raise ValueError("Each date in course config must be a non-empty YYYY-MM-DD string.")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"Invalid date in course config: {text}. Expected YYYY-MM-DD."
        ) from exc


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_display_name(value: object) -> str | None:
    return _optional_string(value)
