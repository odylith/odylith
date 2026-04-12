---
description: Render Atlas diagrams from the Mermaid catalog without a full governance sync.
argument-hint: [forwarded atlas render flags]
---

Render Atlas diagrams from the Mermaid catalog without a full governance sync.

Forwarded args (from user): `$ARGUMENTS`

1. Run `./.odylith/bin/odylith atlas render --repo-root . $ARGUMENTS` to rebuild the Atlas rendered artifacts from their `.mmd` source-of-truth files under `odylith/atlas/source/`.
2. Use this when only diagram artifacts need to be regenerated and you do not need a full sync pipeline run. Do not hand-edit the rendered Atlas outputs the CLI owns.
3. Report which diagrams were rendered or skipped and whether any source files now need a follow-up edit.
4. If the render reveals a stale source diagram, refresh that source file first and rerun the command instead of patching generated output.
