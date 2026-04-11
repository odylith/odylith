# Upgrade And Recovery

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

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
- Install, upgrade, reinstall, and `doctor --repair` may refresh the managed
  project-root host assets under `.claude/`, `.codex/`, and `.agents/skills/`
  together with `odylith/AGENTS.md`, `odylith/CLAUDE.md`,
  `odylith/agents-guidelines/`, and `odylith/skills/`.
- Those Codex project assets are best-effort host enhancements, not the core
  Odylith boot contract. The baseline Codex lane stays the repo-root
  `AGENTS.md` plus `./.odylith/bin/odylith`, so a local Codex build that
  ignores `.codex/` features should not leave Odylith dead out of the box.
- Install, upgrade, reinstall, and `doctor --repair` now rewrite the effective
  `.codex/config.toml` from the local Codex capability snapshot when possible,
  so hook enablement follows the detected host instead of one static config
  assumption.
- Codex project assets only activate when the repo is trusted by Codex, so a
  healthy install can still require an explicit trust step in the host before
  `.codex/hooks.json` and `.codex/agents/*.toml` take effect.
- After install or upgrade, use
  `./.odylith/bin/odylith codex compatibility --repo-root .` to inspect the
  local Codex capability posture instead of assuming one exact CLI version is
  the only safe release lane.
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
