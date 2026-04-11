---
description: Capture a Casebook bug record from the current failure evidence.
argument-hint: <short failure hint or bug id>
---

Capture a Casebook bug record from the current failure evidence.

Hint (from user): `$ARGUMENTS`

1. Confirm the issue is a real bug with concrete reproduction evidence or failing proof. If `$ARGUMENTS` names an existing bug id (e.g. `CB-103`), open and extend that record rather than creating a new one.
2. Search existing Casebook truth under `odylith/casebook/bugs/` first so you extend the right bug instead of duplicating it.
3. If the bug is new, create or update the source-of-truth record under `odylith/casebook/bugs/` with a stable `- Bug ID: CB-###` field and linked governance ids.
4. Refresh the governed surfaces after the source record changes via `./.odylith/bin/odylith sync --repo-root . --check-only` (or the fuller refresh contract when appropriate).
