# Standup Checker Requirements

## Purpose

This project supports attendance tracking for asynchronous daily standups conducted in Discord threads for a university capstone course.

The long-term goal is to reduce manual review effort by reading Discord thread messages, determining attendance by date, updating a Google Sheet, and generating reports.

This document defines a deliberately narrow initial scope.

## Phase 1 Scope

Phase 1 will:

- Read Discord thread messages for a single team.
- Accept a target date as input.
- Determine which students on that team are present for that date.
- Produce a dry-run attendance report.
- Preserve enough evidence in the output to support manual instructor review.

Phase 1 will not modify any external systems.

## Phase 1 Success Criteria

Phase 1 is successful when the tool can, for one configured team thread:

- retrieve messages relevant to a requested date,
- map messages to known students,
- apply a documented attendance rule,
- and output a reviewable attendance result without writing to Google Sheets.

## Core Functional Requirements

### Inputs

Phase 1 requires:

- a Discord bot token,
- a configured Discord thread or team-specific source,
- a roster for one team,
- a target date,
- and a course timezone.

### Attendance Decision

For Phase 1, the default attendance rule is:

- A student is marked present if they post at least one qualifying message in the configured team thread on the target course date.

Qualifying message assumptions for Phase 1:

- Only thread messages are considered.
- Message content is not interpreted semantically.
- Multiple messages on the same date still count as one present mark.
- Message edits do not change attendance unless explicitly handled later.

### Output

The Phase 1 dry-run report should include:

- target date,
- team identifier,
- rostered students,
- attendance result for each student,
- supporting message metadata for present students,
- and any exceptions or ambiguities.

Message metadata should include enough evidence for auditability, such as:

- Discord username or user ID,
- message ID,
- timestamp,
- and a short content preview if appropriate.

## Non-Functional Requirements

- The tool must be deterministic for the same input data.
- The tool must be reviewable by an instructor without inspecting raw API output.
- The tool must fail clearly when configuration or roster data is incomplete.
- The tool must isolate business rules from external integrations so later phases can evolve safely.

## Assumptions

- Each team has a dedicated Discord thread for standups.
- The course uses one authoritative timezone for attendance dates.
- A roster exists that maps students to Discord identities or can be made to do so.
- Attendance in Phase 1 is binary: present or absent.
- Manual instructor review remains the source of truth if output is ambiguous.

## Open Requirements Questions

These items must be finalized before implementation is considered complete:

- What exact timezone defines the attendance day?
- Are weekends and holidays in scope for attendance checks?
- What happens when a student posts shortly after midnight?
- How should unmapped or changed Discord usernames be handled?
- Is roster mapping based on Discord user ID, username, or both?
- Should deleted messages count if they existed during the review window?
- What report format is preferred for Phase 1: CLI text, CSV, JSON, or markdown?

## Explicitly Deferred

The following are out of scope for Phase 1:

- Google Sheets updates
- AI interpretation of message content
- grading calculations
- scheduled automation
- multi-team analytics
- multi-team ingestion workflows
- participation scoring beyond basic attendance presence
- always-on bot behavior

## Risks

- Discord identity mapping may be unreliable if the roster is incomplete.
- Attendance rules may appear simple but become ambiguous near date boundaries.
- Thread structure may differ across teams, making later generalization harder.
- Manual expectations may drift unless attendance rules are documented precisely.

## Phase 1 Deliverable

The end of Phase 1 is a read-only attendance checker for one team that produces a dry-run report for a single date and is suitable for manual validation.
