# Upgrade And Recovery

- For consumer Odylith-fix requests, stay in diagnosis-only mode until the operator explicitly authorizes a repair path.
- Normal lifecycle:
  - bootstrap once from the target repo root with `curl -fsSL https://odylith.ai/install.sh | bash`
  - upgrade later
  - repair only when something drifted
- Inspection commands:
  - `./.odylith/bin/odylith start --repo-root .`
  - `./.odylith/bin/odylith doctor --repo-root .`
  - `./.odylith/bin/odylith version --repo-root .`
- Mutating operator commands:
  - `./.odylith/bin/odylith upgrade --repo-root .`
  - `./.odylith/bin/odylith reinstall --repo-root . --latest`
  - `./.odylith/bin/odylith dashboard refresh --repo-root .`
  - `./.odylith/bin/odylith doctor --repo-root . --repair`
  - `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair`
  - `./.odylith/bin/odylith doctor --repo-root . --repair --reset-local-state`
  - `./.odylith/bin/odylith off --repo-root .`
  - `./.odylith/bin/odylith on --repo-root .`
  - `./.odylith/bin/odylith uninstall --repo-root .`
- In consumer repos, do not run the mutating commands above as a self-directed Odylith fix. Capture the exact failing command, touched paths, and symptoms for upstream diagnosis instead.
- Upgrade should switch versions only after validation succeeds.
- Recovery should restore a healthy install without manual file surgery.
- Use the reset-local-state repair path when cache, tuning, or derived runtime state looks compromised.
- `off`/`on` are the lightweight switch for coding agents; uninstall removes `.odylith/` runtime integration but keeps the `odylith/` context tree.
  `off` detaches Odylith-first repo-root guidance so Codex falls back to the surrounding repo's default behavior; `on` restores Odylith as the default first path.
- Consumer lane:
  - stays on the installed pinned Odylith-managed runtime
  - keeps repo-code validation on the consumer repo's own toolchain
