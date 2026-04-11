# Odylith Atlas Auto Update

Use this skill only when the user explicitly invokes
`$odylith-atlas-auto-update` or asks to refresh Atlas diagrams from
change-watch metadata.

1. Run `./.odylith/bin/odylith atlas auto-update --repo-root .`.
2. If Atlas auto-update reports no changed paths, say so plainly.
3. If freshness or render gates fail, surface the exact blocker and next
   command instead of widening the task.
