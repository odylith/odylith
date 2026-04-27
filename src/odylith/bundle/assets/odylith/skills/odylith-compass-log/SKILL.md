# Odylith Compass Log

Use this skill only when the user explicitly invokes `$odylith-compass-log` or
asks to append a bounded execution note into Compass.

1. Identify the current workstream, entry kind, and one-sentence summary worth
   preserving.
2. Run `./.odylith/bin/odylith compass log --repo-root . --kind <kind> --summary "<summary>"`.
3. Add `--workstream` and `--component` when the active slice is known and the
   command needs those anchors explicitly.
4. Keep the log entry factual, short, and specific to the current slice.
