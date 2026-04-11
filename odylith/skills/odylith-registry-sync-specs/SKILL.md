# Odylith Registry Sync Specs

Use this skill only when the user explicitly invokes
`$odylith-registry-sync-specs` or asks to sync mapped Compass requirement
evidence into component living specs.

1. Run `./.odylith/bin/odylith governance sync-component-spec-requirements --repo-root .`.
2. Report which components or forensics records updated.
3. If nothing changed, say that plainly instead of implying hidden work.
