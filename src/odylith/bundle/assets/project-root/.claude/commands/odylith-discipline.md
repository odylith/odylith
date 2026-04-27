---
description: Validate Odylith Discipline contracts and zero-credit pressure behavior.
argument-hint: [status|check|explain|validate] [--case-id CASE_ID] [--json]
---

Validate Odylith Discipline contracts and zero-credit pressure behavior.

Forwarded flags from user: `$ARGUMENTS`

1. Use `./.odylith/bin/odylith discipline status --repo-root .` for the human-readable readiness summary.
2. Use `./.odylith/bin/odylith discipline check --repo-root . --intent-file <path>` for the human-readable decision summary.
3. Run `./.odylith/bin/odylith validate discipline --repo-root . $ARGUMENTS` for deterministic proof.
4. For quick benchmark proof, run `./.odylith/bin/odylith benchmark --profile quick --family discipline --no-write-report --json`.

User-facing output must not be a raw JSON field dump. Use `--json` only for
machine verification, tests, or when the user explicitly asks for telemetry.
When summarizing a check in chat, say the decision, the practical reason, the
nearest safe move, and whether the hot path stayed local. Use "Odylith
Discipline" for the human-facing name. Do not surface internal acronyms,
hard-law rows, retention classes, pressure feature lists, transcript-retention
flags, or counter names.
