# Security Hardening

Use this skill when a task changes Odylith's runtime trust boundary,
release-asset verification, workflow supply-chain posture, daemon/process
lifetime, or the documented security contract across consumer, dogfood, and
detached `source-local` lanes.

## Lane Boundary
- Consumer lane:
  - keep `./.odylith/bin/odylith` on a verified managed runtime
  - do not rely on insecure local-release or Sigstore-bypass env vars
- Product-repo maintainer mode:
  - pinned dogfood proves the shipped runtime
  - detached `source-local` is the explicit live-source development posture
  - local hosted-release overrides are allowed only for bounded maintainer
    rehearsal

## Default Flow
- identify the active lane and the exact trust boundary first
- inspect the launcher, runtime trust anchor, release-asset verification, and
  long-lived process paths before editing
- harden code and docs together so the written contract matches the enforced
  boundary
- preserve the narrow `0.1.0`/`0.1.1` upgrade-escape compatibility path
  without weakening the modern trusted-runtime contract
- update Casebook, Radar, Registry, and Security Posture truth when the
  security contract changes materially
- verify no Odylith-owned Python processes remain after the command or timeout
  path finishes

## Canonical Commands
```bash
./.odylith/bin/odylith version --repo-root .
./.odylith/bin/odylith doctor --repo-root . --repair
./.odylith/bin/odylith reinstall --repo-root . --latest
./.odylith/bin/odylith context-engine status --repo-root .
pytest tests/unit/install/test_runtime.py tests/unit/install/test_release_assets.py tests/integration/install/test_manager.py -q
pytest tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_sync_cli_compat.py -q
```

## Rules
- Fail closed on ambiguous runtime or release trust.
- Prefer immutable workflow/action pins over floating tags.
- Do not describe detached `source-local` as a secure immutable lane.
- Keep process-lifetime fixes honest: no retry loop or timeout path is done
  until the owned Python process exits.
