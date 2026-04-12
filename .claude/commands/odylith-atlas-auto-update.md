---
description: Refresh Atlas diagrams from change-watch metadata.
argument-hint: [--dry-run] [forwarded atlas auto-update flags]
---

Refresh Atlas diagrams from change-watch metadata.

Forwarded args (from user): `$ARGUMENTS`

1. Run `./.odylith/bin/odylith atlas auto-update --repo-root . $ARGUMENTS` to fold change-watch metadata into the Atlas catalog and re-render impacted diagrams.
2. Pass `--dry-run` first when you want to preview the auto-update mutation plan without writing files; then rerun without `--dry-run` once the plan looks correct.
3. Report which diagrams the auto-update touched, which were skipped, and whether downstream surfaces (Atlas dashboard, registry catalog) need a follow-up sync.
4. Do not hand-edit the rendered Atlas artifacts the CLI owns; refresh the source `.mmd` and let auto-update reproject it.
