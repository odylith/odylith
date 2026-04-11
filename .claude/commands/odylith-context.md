Resolve a known Odylith anchor into the smallest useful local context packet.

1. Use this only when you already know the exact workstream, component, path, bug id, or diagram id.
2. Run `./.odylith/bin/odylith context --repo-root . <ref>`.
3. Summarize the resolved slice, the governing records or code paths it points at, and the next concrete validation or implementation move.
4. Do not widen into raw repo search until the context packet stops being sufficient.
