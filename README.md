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

## Inputs

Required inputs can be provided as CLI flags or environment variables:

- `DISCORD_BOT_TOKEN`
- `DISCORD_THREAD_ID`
- `ROSTER_FILE`
- `TARGET_DATE` in `YYYY-MM-DD`
- `COURSE_TIMEZONE` such as `America/New_York`

Roster format:

```json
{
  "team_id": "team-alpha",
  "students": [
    {
      "student_id": "s1",
      "name": "Alice Student",
      "discord_user_id": "123456789012345678",
      "discord_username": "alice"
    }
  ]
}
```

`discord_user_id` is preferred for matching. `discord_username` is used as a fallback.

## Usage

Install in editable mode:

```bash
python3 -m pip install -e .
```

Run a dry-run attendance check:

```bash
standup-checker \
  --roster examples/roster.example.json \
  --thread-id 123456789012345678 \
  --target-date 2026-06-13 \
  --timezone America/New_York \
  --format text
```

Use `--format json` for machine-readable output.

## Testing

```bash
python3 -m unittest discover -s tests
```
