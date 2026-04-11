Refresh Compass and wait for the current pass to settle.

1. Run `./.odylith/bin/odylith compass refresh --repo-root . --wait`.
2. Report whether the refresh completed, deferred, or surfaced a provider/runtime blocker.
3. If the refresh is blocked, summarize the blocker instead of retrying blindly.
