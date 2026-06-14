from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, time, timedelta, timezone

from standup_checker.attendance import build_attendance_report
from standup_checker.config import AppConfig, get_env
from standup_checker.discord_api import DiscordClient
from standup_checker.reporting import render_json_report, render_text_report
from standup_checker.roster import load_team
from standup_checker.team_config import resolve_thread_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run Discord standup attendance checker")
    parser.add_argument("--roster", default=get_env("ROSTER_FILE"), help="Path to roster JSON")
    parser.add_argument("--thread-id", default=get_env("DISCORD_THREAD_ID"), help="Discord thread ID")
    parser.add_argument("--team-name", default=get_env("TEAM_NAME"), help="Team name")
    parser.add_argument(
        "--team-config",
        default=get_env("TEAM_CONFIG_FILE"),
        help="Path to team config JSON",
    )
    parser.add_argument(
        "--target-date",
        default=get_env("TARGET_DATE"),
        help="Attendance date in YYYY-MM-DD",
    )
    parser.add_argument(
        "--timezone",
        default=get_env("COURSE_TIMEZONE"),
        help="Course timezone, for example America/New_York",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Report output format",
    )
    parser.add_argument(
        "--bot-token",
        default=get_env("DISCORD_BOT_TOKEN"),
        help="Discord bot token; defaults to DISCORD_BOT_TOKEN",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> AppConfig:
    args = build_parser().parse_args(argv)

    missing = [
        name
        for name, value in (
            ("--roster or ROSTER_FILE", args.roster),
            ("--target-date or TARGET_DATE", args.target_date),
            ("--timezone or COURSE_TIMEZONE", args.timezone),
            ("--bot-token or DISCORD_BOT_TOKEN", args.bot_token),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required inputs: {', '.join(missing)}")

    has_direct_thread = bool(args.thread_id)
    has_team_targeting = bool(args.team_name or args.team_config)
    if not has_direct_thread and not has_team_targeting:
        raise ValueError(
            "Provide --thread-id, or provide both --team-name and --team-config."
        )
    if not has_direct_thread and has_team_targeting and not (args.team_name and args.team_config):
        raise ValueError(
            "Provide both --team-name and --team-config when not using --thread-id."
        )

    try:
        parsed_date = date.fromisoformat(args.target_date)
    except ValueError as exc:
        raise ValueError("Target date must use YYYY-MM-DD.") from exc

    config = AppConfig(
        bot_token=args.bot_token,
        roster_path=args.roster,
        target_date=parsed_date,
        timezone_name=args.timezone,
        report_format=args.format,
        thread_id=args.thread_id,
        team_name=args.team_name,
        team_config_path=args.team_config,
    )
    # Validate timezone early.
    _ = config.timezone
    return config


def main(argv: list[str] | None = None) -> int:
    try:
        config = parse_args(argv)
        team = load_team(config.roster_path)
        if config.team_name and team.team_name != config.team_name:
            raise ValueError(
                f"Roster team '{team.team_name}' does not match requested team '{config.team_name}'."
            )
        thread_id = resolve_thread_id(
            thread_id=config.thread_id,
            team_name=config.team_name,
            team_config_path=config.team_config_path,
        )
        course_timezone = config.timezone
        start_local = datetime.combine(config.target_date, time.min, tzinfo=course_timezone)
        end_local = start_local + timedelta(days=1)
        client = DiscordClient(config.bot_token)
        messages = client.fetch_thread_messages(
            thread_id,
            start_at=start_local.astimezone(timezone.utc),
            end_at=end_local.astimezone(timezone.utc),
        )
        report = build_attendance_report(
            team=team,
            thread_id=thread_id,
            target_date=config.target_date,
            timezone=course_timezone,
            messages=messages,
        )
        renderer = render_json_report if config.report_format == "json" else render_text_report
        print(renderer(report))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
