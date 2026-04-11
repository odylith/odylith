---
description: Build a bounded Odylith plan before implementation.
argument-hint: [<slice-anchor>] (optional workstream id, component, or bug id)
---

Build a bounded Odylith plan before implementation.

Slice anchor (from user): `$ARGUMENTS`

1. Ground the slice with `/odylith-start` or `/odylith-context $ARGUMENTS` first; if `$ARGUMENTS` is empty, derive the anchor from the active workstream or ask the user to name one before planning.
2. Identify the active workstream, component, or governed source-of-truth record that the plan will bind to.
3. Produce a flat execution plan with explicit validation and closeout obligations, grounded in real Odylith truth for the named slice.
4. Keep the plan bounded to the current slice instead of widening into unrelated repo cleanup.
