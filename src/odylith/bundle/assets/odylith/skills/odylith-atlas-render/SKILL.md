# Odylith Atlas Render

Use this skill only when the user explicitly invokes `$odylith-atlas-render`
or asks to render Atlas from the Mermaid catalog.

1. Run `./.odylith/bin/odylith atlas render --repo-root .`.
2. Report whether Atlas rendered cleanly or surfaced a freshness blocker.
3. If freshness blocks the render, say which follow-up command is needed
   rather than retrying blindly.
