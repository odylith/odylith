Run the repo-local Odylith startup contract for the current task.

1. If the task is substantive, run `./.odylith/bin/odylith start --repo-root .`.
2. Do not run `/odylith-context`, `odylith query`, `git status`, broad repo search, or any other repo-inspection command in parallel with startup.
3. If startup cannot narrow the slice but the workstream, component, path, or bug id is already known, run `./.odylith/bin/odylith context --repo-root . <ref>` after startup finishes.
4. Summarize the active workstream, component, or bug and state the next concrete implementation step before broad repo search.
5. Do not skip the Odylith grounding step unless the task is trivial or the launcher is unavailable.
