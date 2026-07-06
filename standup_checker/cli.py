from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from time import sleep as time_sleep

from standup_checker.config import AppConfig, get_env, load_project_dotenv
from standup_checker.discord_api import DiscordClient
from standup_checker.legacy_config_adapter import (
    LEGACY_COMPAT_COURSE,
    LEGACY_COMPAT_TERM,
    adapt_legacy_inputs_to_course_config,
)
from standup_checker.models import (
    AttendanceReport,
    CourseAttendanceReport,
    MessageFetchStats,
    StandupMessage,
    Team,
)
from standup_checker.orchestration import build_course_attendance_report
from standup_checker.reporting import (
    render_csv_course_report,
    render_json_course_report,
    render_json_report,
    render_text_course_report,
    render_text_report,
)
from standup_checker.roster import load_course_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run Discord standup attendance checker")
    parser.add_argument("--roster", default=get_env("ROSTER_FILE"), help="Path to roster JSON")
    parser.add_argument("--course-config", help="Path to canonical course config JSON")
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
        choices=("text", "json", "csv"),
        default="text",
        help="Report output format",
    )
    parser.add_argument(
        "--output-file",
        help="Write report output to a file instead of stdout",
    )
    parser.add_argument(
        "--bot-token",
        default=get_env("DISCORD_BOT_TOKEN"),
        help="Discord bot token; defaults to DISCORD_BOT_TOKEN",
    )
    parser.add_argument(
        "--discord-request-delay-seconds",
        type=float,
        default=1.0,
        help="Seconds to wait between Discord thread/date fetches; defaults to 1.0 for safer pacing",
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
            ("--bot-token or DISCORD_BOT_TOKEN", args.bot_token),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required inputs: {', '.join(missing)}")

    if args.discord_request_delay_seconds < 0:
        raise ValueError("--discord-request-delay-seconds must be non-negative.")

    if args.course_config:
        config = AppConfig(
            bot_token=args.bot_token,
            roster_path=None,
            target_date=None,
            timezone_name=None,
            report_format=args.format,
            output_path=args.output_file,
            discord_request_delay_seconds=args.discord_request_delay_seconds,
            debug_matching=args.debug_matching,
            course_config_path=args.course_config,
        )
        return config

    missing = [
        name
        for name, value in (
            ("--roster or ROSTER_FILE", args.roster),
            ("--target-date or TARGET_DATE", args.target_date),
            ("--timezone or COURSE_TIMEZONE", args.timezone),
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
        output_path=args.output_file,
        discord_request_delay_seconds=args.discord_request_delay_seconds,
        debug_matching=args.debug_matching,
        course_config_path=None,
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
        client = DiscordClient(config.bot_token)
        legacy_mode = config.course_config_path is None
        fetch_stats = MessageFetchStats() if config.debug_matching and legacy_mode else None

        if config.course_config_path:
            if config.debug_matching:
                print(
                    "Debug matching currently applies only to legacy single-team mode.",
                    file=sys.stderr,
                )
            course_config = load_course_config(config.course_config_path)
        else:
            if config.roster_path is None or config.target_date is None or config.timezone_name is None:
                raise ValueError("Legacy mode requires roster, target date, and timezone inputs.")
            course_config = adapt_legacy_inputs_to_course_config(
                roster_path=config.roster_path,
                thread_id=config.thread_id,
                team_name=config.team_name,
                team_config_path=config.team_config_path,
                target_date=config.target_date,
                timezone_name=config.timezone_name,
            )

        aggregate_report = build_course_attendance_report(
            course_config=course_config,
            fetch_thread_messages=_build_fetcher(client, fetch_stats),
            request_delay_seconds=config.discord_request_delay_seconds,
            sleep_fn=time_sleep,
        )
        if fetch_stats is not None:
            report = _extract_legacy_report(aggregate_report)
            print(
                render_matching_debug(
                    team=_legacy_team(report),
                    thread_id=report.thread_id,
                    target_date=report.target_date,
                    timezone_name=report.timezone,
                    start_local=_local_day_start(report),
                    end_local=_local_day_end(report),
                    messages=_legacy_messages(report),
                    report=report,
                    fetch_stats=fetch_stats,
                ),
                file=sys.stderr,
            )
        _write_output(
            render_output(aggregate_report=aggregate_report, report_format=config.report_format),
            output_path=config.output_path,
        )
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _build_fetcher(client: DiscordClient, fetch_stats: MessageFetchStats | None):
    def fetch_thread_messages(thread_id: str, start_at: datetime, end_at: datetime) -> list[StandupMessage]:
        return client.fetch_thread_messages(
            thread_id,
            start_at=start_at,
            end_at=end_at,
            debug_stats=fetch_stats,
        )

    return fetch_thread_messages


def render_output(*, aggregate_report: CourseAttendanceReport, report_format: str) -> str:
    if report_format == "csv":
        if _is_legacy_compat_report(aggregate_report):
            raise ValueError("CSV output requires --course-config.")
        return render_csv_course_report(aggregate_report)

    if _is_legacy_compat_report(aggregate_report):
        report = _extract_legacy_report(aggregate_report)
        renderer = render_json_report if report_format == "json" else render_text_report
        return renderer(report)

    renderer = render_json_course_report if report_format == "json" else render_text_course_report
    return renderer(aggregate_report)


def _write_output(output: str, output_path: str | None = None) -> None:
    final_output = output if output.endswith("\n") else f"{output}\n"
    if output_path is not None:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(final_output)
        return
    sys.stdout.write(final_output)


def _is_legacy_compat_report(report: CourseAttendanceReport) -> bool:
    return (
        report.course == LEGACY_COMPAT_COURSE
        and report.term == LEGACY_COMPAT_TERM
        and len(report.reports) == 1
    )


def _extract_legacy_report(report: CourseAttendanceReport) -> AttendanceReport:
    if not _is_legacy_compat_report(report):
        raise ValueError("Expected a single-report legacy aggregate.")
    return report.reports[0]


def _legacy_team(report: AttendanceReport) -> Team:
    return Team(
        team_name=report.team_name,
        students=[record.student for record in report.records],
    )


def _legacy_messages(report: AttendanceReport) -> list[StandupMessage]:
    return [message for record in report.records for message in record.messages] + report.unmatched_messages


def _local_day_start(report: AttendanceReport) -> datetime:
    return datetime.combine(
        report.target_date,
        time.min,
        tzinfo=_timezone_for_name(report.timezone),
    )


def _local_day_end(report: AttendanceReport) -> datetime:
    return _local_day_start(report) + timedelta(days=1)


def _timezone_for_name(timezone_name: str):
    return AppConfig(
        bot_token="unused",
        roster_path=None,
        target_date=None,
        timezone_name=timezone_name,
        report_format="text",
    ).timezone


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
