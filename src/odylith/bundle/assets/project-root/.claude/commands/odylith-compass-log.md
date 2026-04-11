---
description: Append a bounded execution note into Compass.
argument-hint: <kind> "<summary>" (e.g. implementation "B-084 ladder column landed")
---

Append a bounded execution note into Compass.

Entry (from user): `$ARGUMENTS`

1. Identify the current workstream, kind, and one-sentence summary worth preserving. If `$ARGUMENTS` is empty, derive `<kind>` and `<summary>` from the active slice and confirm before logging.
2. Run `./.odylith/bin/odylith compass log --repo-root . $ARGUMENTS` (or construct the full command with `--kind`, `--summary`, `--workstream`, and `--component` when the arguments do not already carry them).
3. Keep the log entry factual, short, and specific to the current slice. Do not narrate history the user does not need to see in the next standup brief.
