from __future__ import annotations

import json
from pathlib import Path


def resolve_thread_id(
    *,
    thread_id: str | None,
    team_name: str | None,
    team_config_path: str | None,
) -> str:
    if thread_id:
        return thread_id

    if not team_name or not team_config_path:
        raise ValueError(
            "Provide --thread-id, or provide both --team-name and --team-config."
        )

    path = Path(team_config_path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    teams = payload.get("teams")
    if not isinstance(teams, dict):
        raise ValueError("Team config file must contain a teams mapping.")

    team_payload = teams.get(team_name)
    if not isinstance(team_payload, dict):
        raise ValueError(f"Team config is missing an entry for team '{team_name}'.")

    resolved_thread_id = team_payload.get("thread_id")
    if not resolved_thread_id:
        raise ValueError(f"Team '{team_name}' is missing thread_id in team config.")

    return str(resolved_thread_id)
