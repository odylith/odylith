---
description: Refresh the governed Odylith surfaces for the files changed in this task.
argument-hint: [changed_paths...] (optional; derived from the active slice when omitted)
---

Refresh the governed Odylith surfaces for the files changed in this task.

Changed paths (from user): `$ARGUMENTS`

1. Identify the changed source-of-truth paths under `odylith/radar/source/`, `odylith/technical-plans/`, `odylith/casebook/bugs/`, `odylith/registry/source/`, or `odylith/atlas/source/`. If `$ARGUMENTS` lists explicit paths, trust those; otherwise derive the list from the active slice before running the refresh.
2. Run `./.odylith/bin/odylith sync --repo-root . --impact-mode selective $ARGUMENTS`.
3. If the change only needs a narrow dashboard rerender after the sync decision, you may use `./.odylith/bin/odylith dashboard refresh --repo-root . --surfaces <surface>`.
4. Report what refreshed, what still needs manual follow-through, and whether any generated bundle mirrors also needed updating.
