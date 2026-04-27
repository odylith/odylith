---
description: Show pinned, active, and locally available Odylith product versions for this repo.
---

Show pinned, active, and locally available Odylith product versions for this repo.

1. Run `./.odylith/bin/odylith version --repo-root .` and treat its live posture as authoritative over older Compass, shell, or release-history context.
2. Summarize the active runtime version, the pinned consumer version, and any locally available alternates the launcher reports.
3. If the launcher is missing, confirm that from the filesystem first and use Odylith's current repair contract instead of guessing at legacy paths.
4. Use this command before diagnosing install, upgrade, rollback, or launcher state.
