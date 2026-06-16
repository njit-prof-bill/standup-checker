from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone

from standup_checker.attendance import build_attendance_report
from standup_checker.config import AppConfig, get_env, load_project_dotenv
from standup_checker.discord_api import DiscordClient
from standup_checker.models import AttendanceReport, MessageFetchStats, StandupMessage, Team
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
    parser.add_argument(
        "--debug-matching",
        action="store_true",
        help="Print matching and date-filter debug details to stderr",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> AppConfig:
    load_project_dotenv()
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
        debug_matching=args.debug_matching,
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
        fetch_stats = MessageFetchStats() if config.debug_matching else None
        messages = client.fetch_thread_messages(
            thread_id,
            start_at=start_local.astimezone(timezone.utc),
            end_at=end_local.astimezone(timezone.utc),
            debug_stats=fetch_stats,
        )
        report = build_attendance_report(
            team=team,
            thread_id=thread_id,
            target_date=config.target_date,
            timezone=course_timezone,
            messages=messages,
        )
        if config.debug_matching:
            print(
                render_matching_debug(
                    team=team,
                    thread_id=thread_id,
                    target_date=config.target_date,
                    timezone_name=config.timezone_name,
                    start_local=start_local,
                    end_local=end_local,
                    messages=messages,
                    report=report,
                    fetch_stats=fetch_stats or MessageFetchStats(),
                ),
                file=sys.stderr,
            )
        renderer = render_json_report if config.report_format == "json" else render_text_report
        print(renderer(report))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def render_matching_debug(
    *,
    team: Team,
    thread_id: str,
    target_date: date,
    timezone_name: str,
    start_local: datetime,
    end_local: datetime,
    messages: list[StandupMessage],
    report: AttendanceReport,
    fetch_stats: MessageFetchStats,
) -> str:
    roster_usernames = [student.discord_user_id for student in team.students]
    message_author_usernames = [
        message.author_username for message in messages if message.author_username is not None
    ]
    matched_usernames = sorted(
        {
            message.author_username
            for record in report.records
            for message in record.messages
            if message.author_username is not None
        }
    )
    unmatched_usernames = sorted(set(message_author_usernames) - set(roster_usernames))
    unmatched_authors = sorted(
        {
            message.author_username or "unknown"
            for message in report.unmatched_messages
        }
    )
    raw_author_counts = _format_value_counts(fetch_stats.raw_author_usernames)
    filtered_author_counts = _format_value_counts(fetch_stats.filtered_author_usernames)

    lines = [
        "Matching Debug:",
        f"- target_date: {target_date.isoformat()}",
        f"- timezone: {timezone_name}",
        f"- requested_thread_id: {thread_id}",
        f"- local_window_start: {start_local.isoformat()}",
        f"- local_window_end: {end_local.isoformat()}",
        f"- raw_messages_fetched: {fetch_stats.raw_message_count}",
        f"- messages_after_date_filter: {fetch_stats.filtered_message_count}",
        f"- roster_student_count: {len(team.students)}",
        f"- roster_discord_user_id_values: {roster_usernames or ['none']}",
        f"- raw_author_username_values: {raw_author_counts or ['none']}",
        f"- filtered_author_username_values: {filtered_author_counts or ['none']}",
        f"- matched_usernames: {matched_usernames or ['none']}",
        f"- unmatched_usernames: {unmatched_usernames or ['none']}",
        f"- unmatched_message_authors: {unmatched_authors or ['none']}",
    ]
    return "\n".join(lines)


def _format_value_counts(values: list[str]) -> list[str]:
    return [f"{value} x{count}" for value, count in sorted(Counter(values).items())]


if __name__ == "__main__":
    raise SystemExit(main())
