# odylith-casebook-bug-investigation

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use when investigating an existing bug through local repo truth, Odylith packets, and linked runtime evidence.

## Canonical Commands

```bash
odylith context-engine --repo-root . impact <paths...>
odylith context-engine --repo-root . architecture <paths...>
odylith sync --repo-root . --check-only --check-clean
```

## Rules

- Keep investigation grounded in local repo truth and linked historical evidence.
- Governance-learning: if investigation exposes a new durable failure signature or invalidates the
  current diagnosis, update the Casebook record before moving to code changes
  or closeout. Read prior failed mechanisms, failed fix attempts, and
  guardrails first, do not repeat a fix path that already failed, capture new
  mechanism-level learning, and mirror planned work, component-contract
  changes, changed topology, and proof checkpoints into Radar/plans,
  Registry, Atlas, and Compass as applicable.
- Prefer bounded packet assistance over broad repo scans only after the evidence cone is grounded.
