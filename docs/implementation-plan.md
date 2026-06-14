# Standup Checker Implementation Plan

## Objective

Implement a narrow first phase that reads Discord thread messages for a single team and produces a dry-run attendance report for a given date.

No application code is being created yet. This document defines the recommended order of work.

## Phase 1 Definition

Phase 1 includes:

- single-team support,
- read-only Discord message retrieval,
- roster-based attendance determination,
- and dry-run attendance reporting.

Phase 1 excludes:

- Google Sheets updates,
- AI interpretation,
- grading calculations,
- scheduled automation,
- and multi-team analytics.

## Recommended Implementation Sequence

### Step 1: Finalize Requirements

Document and confirm:

- course timezone,
- exact attendance rule,
- roster source and identity mapping strategy,
- Discord bot invite and permission expectations,
- whether thread targeting will use direct thread IDs, team config, or both,
- target report format,
- and whether weekends, holidays, or after-midnight posts need special handling.

Output:

- completed `docs/requirements.md`
- explicit examples of present vs absent cases

### Step 2: Define Input Artifacts

Prepare the non-code project inputs that Phase 1 will rely on:

- sample team roster with explicit Discord identity mappings,
- sample team-to-thread configuration,
- sample Discord thread identifiers,
- example attendance review date,
- and sample message transcripts for validation.

Output:

- documented roster format
- documented team/thread configuration shape
- at least one realistic sample transcript for testing design

### Step 3: Design The Data Model

Define the internal records needed for:

- students,
- normalized messages,
- attendance records,
- and dry-run reports.

Output:

- documented field definitions
- clear separation between raw Discord data and normalized internal data

### Step 4: Implement Read-Only Discord Access

Build the minimum integration needed to:

- authenticate with Discord,
- authenticate with a bot token rather than a personal login,
- access one configured thread,
- and retrieve messages relevant to a target date.

Constraints:

- no write actions,
- no bot commands,
- no multi-team support.

Output:

- raw message retrieval working for one team thread

### Step 5: Implement Message Normalization

Transform Discord message data into a stable internal representation so business logic is isolated from API specifics.

Output:

- normalized message records suitable for attendance evaluation

### Step 6: Implement Attendance Evaluation

Apply the Phase 1 attendance rule to normalized messages for the target date.

Output:

- one attendance decision per student
- explicit handling for unmapped messages and duplicate posts

### Step 7: Implement Dry-Run Reporting

Produce a reviewable report that includes:

- attendance by student,
- supporting message evidence,
- and any exceptions requiring manual review.

Output:

- one dry-run attendance report for a requested date

### Step 8: Add Tests

Focus tests on behavior with the highest risk of incorrect attendance decisions.

Priority areas:

- timezone/date filtering,
- roster matching,
- duplicate messages,
- absent students,
- and ambiguous identities.

Output:

- unit tests for attendance logic
- fixture-based tests for realistic standup transcripts

## Proposed Milestones

### Milestone 1: Requirements Locked

Requirements, assumptions, and deferred scope are documented and agreed.

### Milestone 2: Read-Only Retrieval

The project can access one team thread and return raw messages for a date window.

### Milestone 3: Attendance Engine

The project can convert normalized messages into attendance decisions for one date.

### Milestone 4: Dry-Run Report

The project can generate a manual-review attendance report without modifying external systems.

## Testing Strategy For Phase 1

Phase 1 should emphasize:

- unit tests for attendance rules,
- fixture-driven tests using saved message samples,
- and minimal integration tests around Discord client behavior.

Live end-to-end testing should be limited and used only to verify configuration and retrieval behavior.

## Risks To Address Early

- roster-to-Discord identity mismatches,
- missing or stale team-to-thread configuration,
- unclear date-boundary rules,
- inconsistent thread usage by students,
- and overexpanding Phase 1 beyond a reviewable dry-run workflow.

## Stop Conditions

Do not expand Phase 1 to include:

- Google Sheets write support,
- AI-based message interpretation,
- grading calculations,
- background scheduling,
- or reporting across multiple teams.

Those belong to later phases after the single-team dry-run path is validated.
