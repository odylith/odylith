---
description: Search the local Odylith projection store after concrete anchors already exist.
argument-hint: "<terms>" (e.g. "execution profile ladder claude")
---

Search the local Odylith projection store after you already have concrete anchors.

Search terms (from user): `$ARGUMENTS`

1. Confirm that a workstream, component, path, bug id, or other concrete noun is already known. If `$ARGUMENTS` is empty, ask the user for the terms before proceeding.
2. Run `./.odylith/bin/odylith query --repo-root . "$ARGUMENTS"`.
3. Use the result to narrow the next file reads, tests, or edits instead of expanding into broad unguided repo search.
4. Do not use this as a substitute for the initial `odylith start` or `odylith context` step.
