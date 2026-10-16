# Odylith Compass Log

Use this skill when the user explicitly invokes `$odylith-compass-log`, asks to
append a bounded execution note into Compass, or when a durable decision, proof
checkpoint, failed mechanism, failed simulation class, validation result,
release posture, or stable checkpoint must be preserved by the
governance-learning contract.

1. Identify the current workstream, entry kind, and one-sentence summary worth
   preserving.
2. If the note is about a bug or failed mechanism, search Casebook and related
   governance truth first, read prior failed mechanisms, and do not repeat a
   fix path that already failed.
3. Run `./.odylith/bin/odylith compass log --repo-root . --kind <kind> --summary "<summary>"`.
4. Add `--workstream` and `--component` when the active slice is known and the
   command needs those anchors explicitly.
5. Keep the log entry factual, short, and specific to the current slice.
