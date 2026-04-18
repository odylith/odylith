---
description: Validate Guidance Behavior pressure cases and high-risk guidance contracts.
argument-hint: [--case-id CASE_ID] [--json]
---

Validate Guidance Behavior pressure cases and high-risk guidance contracts.

Forwarded flags from user: `$ARGUMENTS`

1. Run `./.odylith/bin/odylith validate guidance-behavior --repo-root . $ARGUMENTS`.
2. Read the case results, guidance checks, runtime-layer integration, and host/lane guidance-surface contract before claiming the guidance layer is passing.
3. For quick benchmark proof, run `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior` unless the operator asked for a slower or live profile.
4. Treat compact packet summaries as availability evidence only; fresh proof still requires the validator or benchmark result.
