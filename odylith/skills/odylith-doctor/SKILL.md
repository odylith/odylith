# Odylith Doctor

Use this skill only when the user explicitly invokes `$odylith-doctor` or asks
to verify or repair the current Odylith install.

1. Run `./.odylith/bin/odylith doctor --repo-root .` for inspection.
2. Add `--repair` only when the user explicitly asks for repair or when the
   current task is clearly repair-authorized.
3. Add `--reset-local-state` only when the user explicitly wants a stronger
   local-state reset.
4. Report the verified posture or blocker instead of retrying blindly.
