# Upgrade And Recovery

- For consumer Odylith-fix requests, stay in diagnosis-only mode until the operator or maintainer explicitly authorizes a repair path.
- Normal lifecycle:
  - bootstrap once from the target repo root with `curl -fsSL https://odylith.ai/install.sh | bash`
  - upgrade later
  - repair only when something drifted
- Inspection commands:
  - `./.odylith/bin/odylith start --repo-root .`
  - `./.odylith/bin/odylith doctor --repo-root .`
  - `./.odylith/bin/odylith version --repo-root .`
- Mutating maintainer or operator commands:
  - `./.odylith/bin/odylith upgrade --repo-root .`
  - `./.odylith/bin/odylith reinstall --repo-root . --latest`
  - `./.odylith/bin/odylith doctor --repo-root . --repair`
  - `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair`
  - `./.odylith/bin/odylith doctor --repo-root . --repair --reset-local-state`
  - `./.odylith/bin/odylith off --repo-root .`
  - `./.odylith/bin/odylith on --repo-root .`
  - `./.odylith/bin/odylith uninstall --repo-root .`
- In consumer repos, do not run the mutating commands above as a self-directed Odylith fix. Capture the exact failing command, touched paths, and symptoms for the maintainer instead.
- Upgrade should switch versions only after validation succeeds.
- Recovery should restore a healthy install without manual file surgery.
- Use the reset-local-state repair path when cache, tuning, or derived runtime state looks compromised.
- `off`/`on` are the lightweight switch for coding agents; uninstall removes `.odylith/` runtime integration but keeps the `odylith/` context tree.
  `off` detaches Odylith-first repo-root guidance so the current coding host falls back to the surrounding repo's default behavior; `on` restores Odylith as the default first path.
- Consumer lane:
  - stays on the installed pinned Odylith-managed runtime
  - never activates `source-local`
  - keeps repo-code validation on the consumer repo's own toolchain
- Product-repo maintainer mode:
  - pinned dogfood posture stays on the tracked pinned runtime for
    shipped-product proof
  - detached `source-local` posture is the explicit maintainer-only override
    for live-source execution
  - detached `source-local` is not a substitute for pinned dogfood proof or
    release posture
