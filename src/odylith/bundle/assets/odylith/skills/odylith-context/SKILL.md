# Odylith Context

Use this skill only when the user explicitly invokes `$odylith-context` or
asks to resolve a known Odylith anchor into the smallest useful local context.

1. Use this only when an exact anchor already exists, such as a workstream id,
   bug id, component, diagram id, or repo path.
2. Run `./.odylith/bin/odylith context --repo-root . <ref>`.
3. Summarize the resolved slice, the governed records or code paths it points
   at, and the next concrete implementation or validation move.
4. Do not widen into raw repo search until the context packet stops being
   sufficient.
