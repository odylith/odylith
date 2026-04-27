---
description: Create a new Odylith workstream record for a genuinely new slice.
argument-hint: <short-slice-description>
---

Create a new Odylith workstream record for a genuinely new slice.

Slice (from user): `$ARGUMENTS`

1. Search existing Radar, plans, bugs, and Compass context first. If `$ARGUMENTS` already maps to an existing workstream, idea, bug id, or parent slice, extend that record instead of creating a new one.
2. Only create a new workstream when the slice is truly new and cannot be truthfully attached to an existing record; use `$ARGUMENTS` as the slice title seed.
3. Keep the new workstream scoped tightly enough that implementation and validation stay coherent; if `$ARGUMENTS` is empty, ask the user for the slice description before filing anything.
