---
description: Validate Adaptive Agent Operating Character contracts and zero-credit pressure behavior.
argument-hint: [status|check|explain|validate] [--case-id CASE_ID] [--json]
---

Validate Adaptive Agent Operating Character contracts and zero-credit pressure behavior.

Forwarded flags from user: `$ARGUMENTS`

1. Use `./.odylith/bin/odylith character status --repo-root .` for local posture and credit policy.
2. Use `./.odylith/bin/odylith character check --repo-root . --intent-file <path>` when a proposed move needs local admissibility.
3. Run `./.odylith/bin/odylith validate agent-operating-character --repo-root . $ARGUMENTS` for deterministic proof.
4. For quick benchmark proof, run `./.odylith/bin/odylith benchmark --profile quick --family agent_operating_character --no-write-report --json`.
