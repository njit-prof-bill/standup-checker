from __future__ import annotations

from datetime import date

from standup_checker.models import CourseConfig, CourseTeam
from standup_checker.roster import load_team
from standup_checker.team_config import resolve_thread_id

LEGACY_COMPAT_COURSE = "legacy-single-team"
LEGACY_COMPAT_TERM = "legacy-single-team"


def adapt_legacy_inputs_to_course_config(
    *,
    roster_path: str,
    thread_id: str | None,
    team_name: str | None,
    team_config_path: str | None,
    target_date: date,
    timezone_name: str,
) -> CourseConfig:
    team = load_team(roster_path)
    if team_name and team.team_name != team_name:
        raise ValueError(
            f"Roster team '{team.team_name}' does not match requested team '{team_name}'."
        )

    resolved_thread_id = resolve_thread_id(
        thread_id=thread_id,
        team_name=team_name,
        team_config_path=team_config_path,
    )

    return CourseConfig(
        course=LEGACY_COMPAT_COURSE,
        term=LEGACY_COMPAT_TERM,
        timezone=timezone_name,
        dates=[target_date],
        teams=[
            CourseTeam(
                team_name=team.team_name,
                thread_id=resolved_thread_id,
                students=team.students,
            )
        ],
    )
