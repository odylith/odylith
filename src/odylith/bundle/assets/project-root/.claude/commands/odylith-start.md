Run the repo-local Odylith startup contract for the current task.

1. If the task is substantive, run `./.odylith/bin/odylith start --repo-root .`.
2. If startup cannot narrow the slice but the workstream, component, path, or bug id is already known, run `./.odylith/bin/odylith context --repo-root . <ref>`.
3. Summarize the active workstream, component, or bug and state the next concrete implementation step before broad repo search.
4. Do not skip the Odylith grounding step unless the task is trivial or the launcher is unavailable.
