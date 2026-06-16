# standup-checker

Phase 1 reads messages from a single Discord standup thread and produces a dry-run attendance report for one date.

## Scope

Implemented:

- read-only Discord thread message retrieval
- roster-based attendance matching
- dry-run attendance reporting in text or JSON

Not implemented:

- Google Sheets updates
- AI interpretation
- scheduling
- grading logic

## Discord Setup

This tool uses a Discord bot token. It does not use a personal Discord login.

Before Phase 1 can run:

- the bot must be invited to the CS 490 Discord server
- the bot must be able to view the target team channel or thread
- the bot must have permission to read message history for that thread

Phase 1 assumes each team has an explicit Discord thread ID for its standup thread.

## Inputs

Required inputs can be provided as CLI flags or environment variables:

- `DISCORD_BOT_TOKEN`
- `ROSTER_FILE`
- `TARGET_DATE` in `YYYY-MM-DD`
- `COURSE_TIMEZONE` such as `America/New_York`

Discord targeting must use one of these two models:

- direct targeting with `DISCORD_THREAD_ID` or `--thread-id`
- team-based targeting with `TEAM_NAME` plus `TEAM_CONFIG_FILE`

`TEAM_CONFIG_FILE` maps team names to explicit Discord thread IDs.

Roster format:

```json
{
  "students": [
    {
      "student_id": "s1",
      "student_name": "Alice Student",
      "team_name": "team-alpha",
      "discord_user_id": "alice",
      "discord_display_name": "alice"
    }
  ]
}
```

Each student mapping must include:

- `student_id`
- `student_name`
- `team_name`
- `discord_user_id`
- `discord_display_name`, optional

For the current Phase 1 implementation, `discord_user_id` must contain the student's
Discord `username` value, not the numeric Discord user ID. The field name is temporary
and preserved only to avoid changing the JSON structure during live validation.
`discord_display_name` is optional metadata for review output.

TODO: rename `discord_user_id` to `discord_username` in a later cleanup.

Team config format:

```json
{
  "teams": {
    "team-alpha": {
      "thread_id": "123456789012345678"
    }
  }
}
```

## Usage

Install in editable mode:

```bash
python3 -m pip install -e .
```

Preferred local configuration uses a `.env` file in the project root. The CLI loads `.env`
automatically before parsing arguments, while keeping normal shell environment variables
and explicit CLI flags as higher-precedence overrides.

Example `.env`:

```dotenv
DISCORD_BOT_TOKEN=your-bot-token
ROSTER_FILE=examples/roster.example.json
DISCORD_THREAD_ID=123456789012345678
TARGET_DATE=2026-06-13
COURSE_TIMEZONE=America/New_York
```

Precedence is:

1. explicit CLI flags such as `--bot-token`
2. real environment variables already exported in the shell
3. values loaded from `.env`

For a first live test:

1. Create a `.env` file with `DISCORD_BOT_TOKEN` and the other common inputs you want to reuse.
2. Use the sample roster and replace the student mappings with real Discord usernames.
3. Either provide a known standup `--thread-id` directly or update `examples/team-config.example.json`.
4. Pick a date that already has known check-ins and run with `--format json` first so unmatched users are easy to inspect.

Run a dry-run attendance check:

```bash
standup-checker \
  --roster examples/roster.example.json \
  --thread-id 123456789012345678 \
  --target-date 2026-06-13 \
  --timezone America/New_York \
  --format text
```

Or use a team config file:

```bash
standup-checker \
  --roster examples/roster.example.json \
  --team-name team-alpha \
  --team-config examples/team-config.example.json \
  --target-date 2026-06-13 \
  --timezone America/New_York \
  --format text
```

Use `--format json` for machine-readable output.

## Testing

```bash
python3 -m unittest discover -s tests
```
