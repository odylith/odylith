---
description: Verify the current Odylith install and optionally repair it in place.
argument-hint: [--repair] [--reset-local-state]
---

Verify the current Odylith install and optionally repair it in place.

Forwarded flags (from user): `$ARGUMENTS`

1. Run `./.odylith/bin/odylith doctor --repo-root . $ARGUMENTS` to inspect launcher health, runtime pinning, project assets, and Compass readiness.
2. Treat `--repair` and `--reset-local-state` as writes that change `odylith/` or `.odylith/`. In a consumer repo, do not run repair autonomously unless the operator authorized Odylith mutation.
3. Read the doctor report end-to-end and surface any blockers that need follow-up before further governed work.
4. If the launcher is absent, confirm the missing state from the filesystem before recommending the canonical hosted bootstrap path.
