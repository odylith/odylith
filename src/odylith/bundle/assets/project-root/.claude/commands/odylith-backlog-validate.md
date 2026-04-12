---
description: Validate Radar backlog records and their plan-linkage contracts.
---

Validate Radar backlog records and their plan-linkage contracts.

1. Run `./.odylith/bin/odylith validate backlog-contract --repo-root .` to check Radar workstream invariants, traceability fields, plan bindings, and queue posture.
2. Read the validator output end-to-end. Treat any reported failures as governance drift to fix at the source-of-truth file under `odylith/radar/source/`, not in mirrored or derived surfaces.
3. After fixing the source records, re-run this validator before refreshing wider governance via `/odylith-sync-governance`.
4. Use this command before commit or handoff whenever you have touched Radar backlog truth.
