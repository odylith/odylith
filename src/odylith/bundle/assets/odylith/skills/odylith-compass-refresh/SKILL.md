# Odylith Compass Refresh

Use this skill only when the user explicitly invokes `$odylith-compass-refresh`
or asks to refresh Compass and wait for the current pass to settle.

1. Run `./.odylith/bin/odylith compass deep-refresh --repo-root .`.
2. Report whether the refresh completed, deferred, or surfaced a provider or
   runtime blocker.
3. If the refresh is blocked, summarize the blocker instead of retrying
   blindly.
