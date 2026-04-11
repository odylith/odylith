---
description: Resolve a known Odylith anchor (workstream, component, path, bug id, or diagram id) into the smallest useful local context packet.
argument-hint: <ref> (e.g. B-084, CB-103, src/odylith/runtime/common/agent_runtime_contract.py)
---

Resolve a known Odylith anchor into the smallest useful local context packet.

Anchor (from user): `$ARGUMENTS`

1. Use this only when you already know the exact workstream, component, path, bug id, or diagram id. If `$ARGUMENTS` is empty, ask the user for the anchor before proceeding.
2. Run `./.odylith/bin/odylith context --repo-root . $ARGUMENTS`.
3. Summarize the resolved slice, the governing records or code paths it points at, and the next concrete validation or implementation move.
4. Do not widen into raw repo search until the context packet stops being sufficient.
