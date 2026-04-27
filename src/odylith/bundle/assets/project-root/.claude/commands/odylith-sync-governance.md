---
description: Refresh the governed Odylith surfaces for the files changed in this task.
argument-hint: [changed_paths...] (optional; derived from the active slice when omitted)
---

Refresh the governed Odylith surfaces for the files changed in this task.

Changed paths (from user): `$ARGUMENTS`

1. Identify the changed source-of-truth paths under `odylith/radar/source/`, `odylith/technical-plans/`, `odylith/casebook/bugs/`, `odylith/registry/source/`, or `odylith/atlas/source/`. If `$ARGUMENTS` lists explicit paths, trust those; otherwise derive the list from the active slice before running the refresh.
2. Run `./.odylith/bin/odylith sync --repo-root . --impact-mode selective $ARGUMENTS`.
3. If the change only needs a narrow visible rerender after the sync decision, use the owned-surface command for the touched slice: `./.odylith/bin/odylith radar refresh --repo-root .`, `./.odylith/bin/odylith registry refresh --repo-root .`, `./.odylith/bin/odylith casebook refresh --repo-root .`, `./.odylith/bin/odylith atlas refresh --repo-root . --atlas-sync`, or `./.odylith/bin/odylith compass refresh --repo-root . --wait`.
4. Report what refreshed, what still needs manual follow-through, and whether any generated bundle mirrors also needed updating.
