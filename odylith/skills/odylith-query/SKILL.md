# Odylith Query

Use this skill only when the user explicitly invokes `$odylith-query` or asks
to search the local Odylith projection store after concrete anchors already
exist.

1. Confirm that a concrete noun already exists, such as a workstream,
   component, path, bug id, or diagram id.
2. Run `./.odylith/bin/odylith query --repo-root . "<terms>"`.
3. Use the result to narrow the next file reads, tests, or edits instead of
   expanding into broad unguided repo search.
4. Do not use this as a substitute for the initial Odylith grounding step.
