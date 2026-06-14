# Standup Checker Architecture

## Overview

This project should be structured as a small, modular pipeline rather than a monolithic script.

Phase 1 architecture should support one workflow:

1. load configuration,
2. load roster data for one team,
3. resolve the target Discord thread ID,
4. read Discord thread messages,
5. normalize messages into an internal format,
6. apply attendance rules for a target date,
7. produce a dry-run attendance report.

Thread resolution in Phase 1 must support either:

- a direct CLI or environment-supplied thread ID
- or a team config file that maps team names to thread IDs

Discord access for Phase 1 must be bot-based:

- the tool uses a Discord bot token
- the bot must be invited to the CS 490 server
- the bot must have permission to view the target team thread and read message history

Even though external integrations are deferred for later expansion, the code structure should still separate:

- domain logic,
- integration logic,
- and presentation/reporting logic.

## Architectural Goals

- Keep attendance rules independent from Discord-specific payload shapes.
- Keep reporting independent from attendance calculation.
- Keep external writes out of Phase 1 entirely.
- Support later extension to more teams and Google Sheets without rewriting the core attendance engine.

## Proposed High-Level Components

### Configuration Layer

Responsible for:

- reading environment-based settings,
- validating required configuration,
- loading target date and team context,
- resolving thread targeting from either direct thread ID input or team config,
- and locating roster/configuration files.

### Roster Layer

Responsible for:

- loading roster data for one team,
- resolving student identity mappings from student name, team name, Discord user ID, and optional display name,
- and exposing a stable set of students expected for attendance.

### Discord Reader

Responsible for:

- retrieving messages from a configured Discord thread,
- constraining retrieval to the requested window when possible,
- and returning raw message data.

This is an integration boundary and should not contain attendance rules.

### Message Normalizer

Responsible for transforming raw Discord payloads into a stable internal record with fields such as:

- message ID,
- author identity,
- timestamp,
- thread identifier,
- and content preview.

This layer protects the rest of the system from Discord API details.

### Attendance Engine

Responsible for:

- filtering messages for the target course date,
- matching messages to rostered students,
- applying the attendance rule,
- and producing one attendance record per student.

This is the core business logic and should be the easiest part to unit test.

### Report Generator

Responsible for turning attendance results into a dry-run output format suitable for manual review.

Possible outputs for Phase 1:

- CLI summary,
- JSON,
- CSV,
- or markdown.

The final Phase 1 implementation can choose one primary format and optionally support one machine-readable format.

## Proposed Data Flow

1. Configuration is loaded and validated.
2. The roster for one team is loaded.
3. The target thread ID is resolved from direct input or team configuration.
4. Discord messages are fetched for the configured thread.
5. Raw messages are normalized.
6. The attendance engine evaluates the target date.
7. A dry-run report is generated.

## Internal Data Model

Phase 1 should define these conceptual entities:

- `Student`
  - roster identity for one student
- `Team`
  - the single configured team context
- `TeamThreadConfig`
  - mapping from team name to Discord thread ID
- `StandupMessage`
  - normalized Discord message data
- `AttendanceRecord`
  - result for one student on one date
- `AttendanceReport`
  - aggregate report for the team and date

These are documentation concepts for now, not implementation instructions.

## Boundaries And Responsibilities

### Must Stay Outside Phase 1

- Google Sheets write paths
- grade calculation logic
- AI or NLP-based interpretation
- cron/scheduled execution concerns
- cross-team aggregation and dashboards

### Should Be Designed For Later

- ability to swap report formats,
- ability to add more teams,
- ability to support persistence/output sinks later,
- and ability to reuse the attendance engine across different orchestration modes.

## Error Handling Expectations

Phase 1 should fail fast and clearly for:

- missing configuration,
- invalid target date,
- missing roster mappings,
- missing team-to-thread mappings when team-based targeting is used,
- inaccessible Discord thread,
- and ambiguous identity matches.

Errors should be descriptive enough that an instructor or developer can correct inputs without deep debugging.

## Testing Implications

The architecture should make it straightforward to test:

- attendance rules from normalized message fixtures,
- date boundary behavior,
- student identity mapping behavior,
- and report formatting independent of Discord access.

The attendance engine and report generator should be testable without live Discord access.
