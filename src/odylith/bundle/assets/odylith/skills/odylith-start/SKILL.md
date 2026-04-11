# Odylith Start

Use this skill only when the user explicitly invokes `$odylith-start` or
directly asks to run the repo-local Odylith startup contract.

1. Run `./.odylith/bin/odylith start --repo-root .` for substantive work.
2. If startup cannot narrow the slice but the user already named a workstream,
   bug, component, or path, follow with
   `./.odylith/bin/odylith context --repo-root . <ref>`.
3. Keep the next repo reads bounded to the resolved slice instead of widening
   into broad repo search immediately.
4. Summarize only the active slice and the next concrete move; do not narrate
   control-plane internals.
