# First Live Validation Guide

This guide walks through the first real-world validation of `standup-checker` against an actual Discord standup thread.

The goal is narrow:

1. create a Discord bot,
2. invite it to the correct server,
3. collect the IDs needed by the tool,
4. populate the roster and team config files,
5. run the tool against one real thread for one real date,
6. compare the output to what you expect from manual review.

## Before You Start

You should have:

- a Discord account with permission to add apps to the target server,
- a test date that already has known standup activity,
- a team roster with each student’s Discord account identified,
- this repository available locally,
- and Python 3.11+ installed.

For the first live validation, use a team and date where you already know roughly who posted. That makes it much easier to spot identity or date-boundary problems quickly.

## Preferred Local Setup: `.env`

The preferred workflow is to keep reusable local inputs in a `.env` file in the repository root.
The CLI loads `.env` automatically before argument parsing.

Typical `.env` contents:

```dotenv
DISCORD_BOT_TOKEN=your-bot-token
ROSTER_FILE=path/to/real-roster.json
DISCORD_THREAD_ID=123456789012345678
TARGET_DATE=2026-06-13
COURSE_TIMEZONE=America/New_York
```

Precedence is:

1. explicit CLI flags such as `--bot-token`
2. real environment variables already exported in your shell
3. values loaded from `.env`

That means:

- `.env` is the normal place to keep your bot token for local use,
- exported shell variables can temporarily override `.env`,
- and passing `--bot-token` overrides both.

## 1. Create a Discord Bot

1. Go to the Discord Developer Portal.
2. Create a new application.
3. Give the application a recognizable name such as `standup-checker`.
4. Open the application settings and go to the `Bot` section.
5. Confirm that the bot user exists. New applications normally create one by default.
6. Generate or reset the bot token.
7. Store the token somewhere safe. For local use, place it in `.env` as `DISCORD_BOT_TOKEN`.

Important:

- Treat the bot token like a password.
- Do not commit it to the repository.
- If you accidentally expose it, reset it immediately in the Developer Portal.

## 2. Invite the Bot to Your Server

1. In the Developer Portal, open the application’s `Installation` settings.
2. Use a guild/server install flow.
3. Include the `bot` scope.
4. Generate the install link.
5. Open the link while logged into Discord.
6. Choose the target server.
7. Authorize the installation.

The account performing the install must have permission to add apps to that server.

## 3. Required Permissions

This project is read-only. The bot does not need message-send permissions for Phase 1.

Minimum practical access:

- `View Channel`
- `Read Message History`

If the standup thread is inside a private channel or a private forum-style area, the bot must also be able to see the parent location that contains the thread.

Notes:

- No Google Sheets permissions are involved in Phase 1.
- No slash-command setup is required for this tool.
- No message content interpretation is performed by the tool.

## 4. Obtain the Required Discord IDs

The tool itself needs:

- thread ID,
- Discord user IDs for each student,
- and a bot token.

You also asked for the server ID. The current tool does not consume it, but it is still useful for manual verification and recordkeeping.

### Enable Developer Mode

In Discord, enable `Developer Mode` first. Discord’s UI can move around over time, but it is typically under advanced app settings. Once enabled, Discord adds `Copy ID` options to right-click menus.

### Guild / Server ID

1. In Discord, find the target server in the left sidebar.
2. Right-click the server icon or server name.
3. Select `Copy Server ID` or `Copy ID`.
4. Save that value in your validation notes.

### Thread ID

1. Open the exact standup thread you want to validate.
2. Right-click the thread name, thread entry, or thread header.
3. Select `Copy ID`.
4. Save that value. This is the value to use as `thread_id`.

Be careful to copy the thread ID, not just the parent channel ID.

### Discord User IDs

For each student:

1. Find the student in the member list or in one of their messages.
2. Right-click their username or avatar.
3. Select `Copy User ID` or `Copy ID`.
4. Save that value for the roster file.

Use the actual numeric user ID, not the visible display name. Display names can change; user IDs are stable and are the matching key used by this project.

## 5. Populate the Roster File

Use [examples/roster.example.json](../examples/roster.example.json) as the template.

Each student entry must include:

- `student_id`: your course or roster identifier for the student
- `student_name`: the human-readable student name
- `team_name`: the team this roster belongs to
- `discord_user_id`: the student’s numeric Discord user ID

Optional field:

- `discord_display_name`: the current Discord display name, useful for manual review output

Rules to follow:

- Put only one team in a single roster file.
- Keep `team_name` identical for every student in that file.
- Make sure every `discord_user_id` is unique.
- Prefer real user IDs collected directly from Discord instead of copied usernames.

Recommended first-pass workflow:

1. Start from the example roster file.
2. Replace the sample students with the real students for one team.
3. Double-check each `discord_user_id` before running the tool.
4. Keep the file small and limited to one known team for the first validation.

## 6. Populate the Team Config File

Use [examples/team-config.example.json](../examples/team-config.example.json) as the template.

This file maps a team name to a Discord thread ID.

Each team entry needs:

- team name key under `teams`
- `thread_id` inside that team’s object

Rules to follow:

- The team name here must exactly match the `team_name` used in the roster file.
- The thread ID must be the exact standup thread ID copied from Discord.

For the first live validation, a single team entry is enough.

## 7. Run the Tool Against a Real Thread

There are two supported ways to target the thread:

1. direct thread targeting with `--thread-id`
2. team-based targeting with `--team-name` plus `--team-config`

The simplest first live validation is usually direct thread targeting, because it removes one extra variable.

### Preparation

Before running:

1. install the project in your environment if you have not already,
2. create or update `.env` with `DISCORD_BOT_TOKEN`,
3. choose a roster file with real student IDs,
4. choose a target date that already has standup posts,
5. set the course timezone correctly.

### Recommended First Run

Use:

- the real roster file,
- the real thread ID,
- a known target date,
- the course timezone,
- and `--format json`.

JSON is the best first validation format because it makes unmatched messages and per-student evidence easier to inspect.

After the JSON run looks correct, run again with `--format text` if you want a more human-readable review output.

### Direct Thread Run

Example shape:

```bash
standup-checker \
  --roster path/to/real-roster.json \
  --thread-id 123456789012345678 \
  --target-date 2026-06-13 \
  --timezone America/New_York \
  --bot-token "$DISCORD_BOT_TOKEN" \
  --format json
```

### Team Config Run

Example shape:

```bash
standup-checker \
  --roster path/to/real-roster.json \
  --team-name team-alpha \
  --team-config path/to/team-config.json \
  --target-date 2026-06-13 \
  --timezone America/New_York \
  --bot-token "$DISCORD_BOT_TOKEN" \
  --format json
```

## 8. Interpret the Results

The Phase 1 result is a dry-run attendance report. It does not write to any external system.

### What “present” means

A student is marked `present` if the tool found at least one message in the target thread during the requested date window and that message author matched the student’s `discord_user_id`.

### What to review in the output

For each student:

- whether they were marked `present` or `absent`
- which message IDs were used as evidence
- the timestamps of those messages
- the content preview shown for those messages

Also review the `unmatched_messages` section carefully.

That section usually means one of these things:

- someone posted in the thread who is not in the roster,
- a rostered student’s Discord user ID was entered incorrectly,
- the wrong thread was checked,
- or a non-student account posted in the thread.

### How to validate the first live run

For the first validation, compare the tool output against manual inspection of the same thread for the same date.

Check:

1. every student you expect to be present is marked present,
2. every student you expect to be absent is marked absent,
3. timestamps fall on the expected course date,
4. no legitimate student messages appear under `unmatched_messages`,
5. and no roster student is missing because of a bad `discord_user_id`.

### Common result patterns

If a student is unexpectedly absent:

- verify their `discord_user_id` in the roster,
- verify they posted in that exact thread,
- verify the target date and timezone,
- and check whether they posted just before or after midnight.

If there are many unmatched messages:

- confirm you copied user IDs correctly,
- confirm the roster is for the correct team,
- confirm the selected thread is the actual standup thread,
- and confirm other participants such as instructors or bots are expected to appear.

If the tool returns a Discord access error:

- confirm the bot token is correct,
- confirm the bot was invited to the correct server,
- confirm the bot can view the thread,
- and confirm it has `Read Message History`.

## Recommended First Live Validation Sequence

1. Choose one team.
2. Choose one date with known standup activity.
3. Collect the thread ID and user IDs directly from Discord.
4. Populate the roster file carefully.
5. Run with direct `--thread-id` and `--format json`.
6. Compare the output to manual review of the thread.
7. Correct any roster or thread-ID mistakes.
8. Repeat the run until the dry-run output matches manual expectations.
9. Once the direct-thread run is validated, test the team-config path.

## Outcome of a Successful Validation

Your first live validation is successful when:

- the bot can read the target thread,
- the rostered students are matched correctly by Discord user ID,
- the report matches manual review for the chosen date,
- and any unmatched messages are explainable.

## References

- Discord Developer Docs: Building your first Discord Bot: https://docs.discord.com/developers/quick-start/getting-started
- Discord Developer Docs: OAuth2: https://docs.discord.com/developers/topics/oauth2
