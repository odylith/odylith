---
description: Prepare a bounded handoff for the active Odylith slice.
argument-hint: [<slice-anchor>] (optional workstream id, component, or bug id)
---

Prepare a bounded handoff for the active Odylith slice.

Slice anchor (from user): `$ARGUMENTS`

1. Ground the slice with `/odylith-context $ARGUMENTS` if a workstream, bug, or component id is known; if `$ARGUMENTS` is empty, derive the active slice from Compass runtime state before writing the handoff.
2. Summarize current state, remaining work, validation status, and governed records that changed for the named slice.
3. Keep the handoff tied to the active slice so the next session can resume without rediscovery.
