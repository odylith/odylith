# Coding Standards

## Scope And Precedence
- This file is the shared Odylith coding baseline that may reach the consumer
  lane.
- For consumer-owned code, the consumer repo's own `AGENTS.md`, coding
  standards, and validation/tooling rules take precedence.
- Maintainer-only Odylith product coding policy lives in
  `../maintainer/agents-guidelines/CODING_STANDARDS.md`.

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

## Shared Documentation, Reuse, And Robustness
- Clear code documentation, reusability, and robustness are non-negotiable.
- Prefer extending shared helpers, shared contracts, and existing runtime
  primitives over copy-paste or near-duplicate logic.
- If equivalent behavior already exists, reuse it or consolidate toward one
  canonical implementation instead of growing a parallel fork.
- When behavior changes would otherwise stop being obvious to the next
  maintainer, update the governing doc, spec, or nearest high-signal code
  comment in the same change.
- Add or tighten inline code documentation only when it clarifies non-obvious
  invariants, state transitions, pressure cases, or boundary assumptions. Do
  not add filler comments to obvious code.
- New helpers should stay bounded, named for the real contract they carry, and
  covered by focused validation rather than introduced as one-off glue.

## Shared Validation Expectations
- Every coding change should carry focused validation that proves the real
  contract touched by the change.
- In consumer repos, validate consumer-owned code with the consumer repo's own
  toolchain and rule set after Odylith narrows the slice.
- Use [VALIDATION_AND_TESTING.md](./VALIDATION_AND_TESTING.md) for the full
  proof bundles and command-level validation guidance for Odylith-owned
  product surfaces.
