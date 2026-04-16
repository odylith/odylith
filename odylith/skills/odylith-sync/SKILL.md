# Odylith Sync

Use this skill only when the user explicitly invokes `$odylith-sync` or asks
to refresh governed Odylith surfaces for the current changed slice.

1. Identify the changed source-of-truth paths under `odylith/radar/source/`,
   `odylith/technical-plans/`, `odylith/casebook/bugs/`,
   `odylith/registry/source/`, `odylith/atlas/source/`, or other governed
   Odylith paths.
2. Run `./.odylith/bin/odylith sync --repo-root . --impact-mode selective <changed_paths...>`.
3. If the change only needs a narrow rerender after the sync decision, you may
   use the owned-surface command for the touched slice:
   `./.odylith/bin/odylith radar refresh --repo-root .`,
   `./.odylith/bin/odylith registry refresh --repo-root .`,
   `./.odylith/bin/odylith casebook validate --repo-root .`,
   `./.odylith/bin/odylith casebook refresh --repo-root .`,
   `./.odylith/bin/odylith atlas refresh --repo-root . --atlas-sync`,
   `./.odylith/bin/odylith compass refresh --repo-root .`, or
   `./.odylith/bin/odylith compass deep-refresh --repo-root .` when the
   rerender also needs standup-brief settlement.
4. Report what refreshed, what still needs manual follow-through, and whether
   generated bundle mirrors also changed.
