from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from standup_checker.models import CourseConfig, CourseTeam, StandupMessage, Student
from standup_checker.orchestration import build_course_attendance_report


class CourseAttendanceOrchestrationTests(unittest.TestCase):
    def test_one_team_one_date(self) -> None:
        config = self._course_config(
            dates=[date(2026, 6, 13)],
            teams=[
                self._course_team(
                    team_name="team-1",
                    thread_id="thread-1",
                    students=[self._student("s1", "Alice", "team-1", "alice")],
                )
            ],
        )

        def fetch_thread_messages(thread_id: str, start_at: datetime, end_at: datetime) -> list[StandupMessage]:
            self.assertEqual(thread_id, "thread-1")
            self.assertEqual(start_at, datetime(2026, 6, 13, 4, 0, tzinfo=timezone.utc))
            self.assertEqual(end_at, datetime(2026, 6, 14, 4, 0, tzinfo=timezone.utc))
            return [self._message("m1", "alice", "thread-1", "2026-06-13T14:00:00+00:00")]

        aggregate = build_course_attendance_report(
            course_config=config,
            fetch_thread_messages=fetch_thread_messages,
        )

        self.assertEqual(aggregate.course, "CS 490")
        self.assertEqual(aggregate.term, "Summer 2026")
        self.assertEqual(aggregate.timezone, "America/New_York")
        self.assertEqual(len(aggregate.reports), 1)
        self.assertEqual(aggregate.reports[0].team_name, "team-1")
        self.assertEqual(aggregate.reports[0].target_date, date(2026, 6, 13))
        self.assertEqual([record.present for record in aggregate.reports[0].records], [True])

    def test_one_team_multiple_dates(self) -> None:
        config = self._course_config(
            dates=[date(2026, 6, 13), date(2026, 6, 14)],
            teams=[
                self._course_team(
                    team_name="team-1",
                    thread_id="thread-1",
                    students=[self._student("s1", "Alice", "team-1", "alice")],
                )
            ],
        )
        calls: list[tuple[str, datetime, datetime]] = []

        def fetch_thread_messages(thread_id: str, start_at: datetime, end_at: datetime) -> list[StandupMessage]:
            calls.append((thread_id, start_at, end_at))
            if start_at == datetime(2026, 6, 13, 4, 0, tzinfo=timezone.utc):
                return [self._message("m1", "alice", "thread-1", "2026-06-13T14:00:00+00:00")]
            return []

        aggregate = build_course_attendance_report(
            course_config=config,
            fetch_thread_messages=fetch_thread_messages,
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(
            [(report.target_date, report.records[0].present) for report in aggregate.reports],
            [(date(2026, 6, 13), True), (date(2026, 6, 14), False)],
        )

    def test_multiple_teams_one_date(self) -> None:
        config = self._course_config(
            dates=[date(2026, 6, 13)],
            teams=[
                self._course_team(
                    team_name="team-1",
                    thread_id="thread-1",
                    students=[self._student("s1", "Alice", "team-1", "alice")],
                ),
                self._course_team(
                    team_name="team-2",
                    thread_id="thread-2",
                    students=[self._student("s2", "Bob", "team-2", "bob")],
                ),
            ],
        )

        def fetch_thread_messages(thread_id: str, start_at: datetime, end_at: datetime) -> list[StandupMessage]:
            del start_at, end_at
            if thread_id == "thread-1":
                return [self._message("m1", "alice", "thread-1", "2026-06-13T14:00:00+00:00")]
            return [self._message("m2", "bob", "thread-2", "2026-06-13T15:00:00+00:00")]

        aggregate = build_course_attendance_report(
            course_config=config,
            fetch_thread_messages=fetch_thread_messages,
        )

        self.assertEqual(
            [(report.team_name, report.records[0].present) for report in aggregate.reports],
            [("team-1", True), ("team-2", True)],
        )

    def test_multiple_teams_multiple_dates(self) -> None:
        config = self._course_config(
            dates=[date(2026, 6, 13), date(2026, 6, 14)],
            teams=[
                self._course_team(
                    team_name="team-1",
                    thread_id="thread-1",
                    students=[self._student("s1", "Alice", "team-1", "alice")],
                ),
                self._course_team(
                    team_name="team-2",
                    thread_id="thread-2",
                    students=[self._student("s2", "Bob", "team-2", "bob")],
                ),
            ],
        )

        def fetch_thread_messages(thread_id: str, start_at: datetime, end_at: datetime) -> list[StandupMessage]:
            del end_at
            if thread_id == "thread-1" and start_at == datetime(2026, 6, 13, 4, 0, tzinfo=timezone.utc):
                return [self._message("m1", "alice", "thread-1", "2026-06-13T14:00:00+00:00")]
            if thread_id == "thread-2" and start_at == datetime(2026, 6, 14, 4, 0, tzinfo=timezone.utc):
                return [self._message("m2", "bob", "thread-2", "2026-06-14T14:00:00+00:00")]
            return []

        aggregate = build_course_attendance_report(
            course_config=config,
            fetch_thread_messages=fetch_thread_messages,
        )

        self.assertEqual(
            [
                (report.team_name, report.target_date, report.records[0].present)
                for report in aggregate.reports
            ],
            [
                ("team-1", date(2026, 6, 13), True),
                ("team-1", date(2026, 6, 14), False),
                ("team-2", date(2026, 6, 13), False),
                ("team-2", date(2026, 6, 14), True),
            ],
        )

    def test_messages_from_one_team_do_not_mark_students_in_another_team_present(self) -> None:
        config = self._course_config(
            dates=[date(2026, 6, 13)],
            teams=[
                self._course_team(
                    team_name="team-1",
                    thread_id="thread-1",
                    students=[self._student("s1", "Alice", "team-1", "alice")],
                ),
                self._course_team(
                    team_name="team-2",
                    thread_id="thread-2",
                    students=[self._student("s2", "Alice Clone", "team-2", "alice")],
                ),
            ],
        )

        def fetch_thread_messages(thread_id: str, start_at: datetime, end_at: datetime) -> list[StandupMessage]:
            del start_at, end_at
            if thread_id == "thread-1":
                return [self._message("m1", "alice", "thread-1", "2026-06-13T14:00:00+00:00")]
            return []

        aggregate = build_course_attendance_report(
            course_config=config,
            fetch_thread_messages=fetch_thread_messages,
        )

        self.assertEqual(
            [(report.team_name, report.records[0].present) for report in aggregate.reports],
            [("team-1", True), ("team-2", False)],
        )

    def _course_config(self, *, dates: list[date], teams: list[CourseTeam]) -> CourseConfig:
        return CourseConfig(
            course="CS 490",
            term="Summer 2026",
            timezone="America/New_York",
            dates=dates,
            teams=teams,
        )

    def _course_team(
        self,
        *,
        team_name: str,
        thread_id: str,
        students: list[Student],
    ) -> CourseTeam:
        return CourseTeam(
            team_name=team_name,
            thread_id=thread_id,
            students=students,
        )

    def _student(
        self,
        student_id: str,
        student_name: str,
        team_name: str,
        discord_user_id: str,
    ) -> Student:
        return Student(
            student_id=student_id,
            student_name=student_name,
            team_name=team_name,
            discord_user_id=discord_user_id,
        )

    def _message(
        self,
        message_id: str,
        author_username: str,
        thread_id: str,
        created_at_iso: str,
    ) -> StandupMessage:
        return StandupMessage(
            message_id=message_id,
            author_id="100",
            author_username=author_username,
            created_at=datetime.fromisoformat(created_at_iso),
            content="Daily standup",
            thread_id=thread_id,
        )


if __name__ == "__main__":
    unittest.main()
