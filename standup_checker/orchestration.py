from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from time import sleep as time_sleep
from typing import Callable, Protocol
from zoneinfo import ZoneInfo

from standup_checker.attendance import build_attendance_report
from standup_checker.models import CourseAttendanceReport, CourseConfig, StandupMessage, Team


class FetchThreadMessages(Protocol):
    def __call__(
        self,
        thread_id: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[StandupMessage]:
        ...


def build_course_attendance_report(
    *,
    course_config: CourseConfig,
    fetch_thread_messages: FetchThreadMessages,
    request_delay_seconds: float = 1.0,
    sleep_fn: Callable[[float], None] = time_sleep,
) -> CourseAttendanceReport:
    course_timezone = ZoneInfo(course_config.timezone)
    reports = []
    fetch_count = 0
    total_fetches = len(course_config.teams) * len(course_config.dates)

    for course_team in course_config.teams:
        team = Team(
            team_name=course_team.team_name,
            students=course_team.students,
        )
        for target_date in course_config.dates:
            start_local = datetime.combine(target_date, time.min, tzinfo=course_timezone)
            end_local = start_local + timedelta(days=1)
            messages = fetch_thread_messages(
                thread_id=course_team.thread_id,
                start_at=start_local.astimezone(timezone.utc),
                end_at=end_local.astimezone(timezone.utc),
            )
            reports.append(
                build_attendance_report(
                    team=team,
                    thread_id=course_team.thread_id,
                    target_date=target_date,
                    timezone=course_timezone,
                    messages=messages,
                )
            )
            fetch_count += 1
            if fetch_count < total_fetches and request_delay_seconds > 0:
                sleep_fn(request_delay_seconds)

    return CourseAttendanceReport(
        course=course_config.course,
        term=course_config.term,
        timezone=course_config.timezone,
        reports=reports,
    )
