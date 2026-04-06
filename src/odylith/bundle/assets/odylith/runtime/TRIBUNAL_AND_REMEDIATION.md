# Tribunal and Remediation

Installed Odylith owns the governance reasoning and action loop:

1. `odylith sync` refreshes deterministic posture and scope synthesis.
2. Tribunal turns eligible scopes into ranked dossiers and an engineering
   brief.
3. Remediator compiles bounded correction packets with validation, rollback, and
   stale guards.
4. Odylith records approval, delegation, apply, and clearance back into
   `.odylith/runtime/`.

Primary operator commands:

```bash
odylith sync --repo-root . --force
odylith context-engine --repo-root . status
odylith compass log --repo-root . --kind decision --summary "<decision>"
odylith compass update --repo-root . --statement "<current state>"
```

Consumer repositories keep local plans, bugs, specs, runbooks, and registry
truth in place. Odylith reads those inputs; it does not become their source of
truth.
