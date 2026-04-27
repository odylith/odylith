---
status: finished
idea_id: B-032
title: v0.1.5 Agent-First Operator Workflow and Recovery Polish
date: 2026-03-30
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: first-turn agent entrypoint, long-running command progress UX, surface-scoped refresh, reinstall semantics, dry-run previews, launcher recovery, docs and CLI contract discipline, dirty-worktree mutation clarity, interpreter/status reporting, and fallback guidance
sizing: L
complexity: High
ordering_score: 100
ordering_rationale: Odylith's underlying install, grounding, and governance mechanics are increasingly solid, but the operator contract still asks too much memory from Codex and too much trust from the user. The next release should make the first command, progress model, mutation scope, recovery path, and fallback behavior explicit enough that Odylith feels safe and zero-friction instead of merely powerful.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-30-odylith-v0-1-5-agent-first-operator-workflow-and-recovery-polish.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-027,B-030,B-031
workstream_blocks:
related_diagram_ids:
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Odylith still makes common turns more manual than they should be. Codex may
have to choose between `version`, `doctor`, `context-engine`, and `sync`
without one supported smart first step. Long-running commands can read hung.
Refresh scope, tracked-file mutation scope, runtime-versus-project-toolchain
ownership, and fallback behavior are still too implicit. Recovery exists, but
the product does not always present it as one obvious self-heal path from the
consumer repo itself.

## Customer
- Primary: consumer-repo operators and coding-agent sessions that expect
  Odylith to feel like the default operating layer immediately after install.
- Secondary: Odylith maintainers dogfooding the same operator contract in the
  product repo and judging whether the release feels polished enough to ship.

## Opportunity
If the next release turns Odylith's operator model into one explicit product
contract, then the product stops depending on remembered command trivia and
unstated heuristics. That should improve adoption, trust, and diagnosis
quality, while reducing the cases where users or agents widen prematurely into
raw repo scan behavior.

## Proposed Solution
Ship this as an umbrella next-release contract with execution waves instead of
one giant patch.

### Wave 1: Smart first-turn entrypoint and narrowing fallback
- add one supported smart first-turn command such as `odylith start` or
  `odylith bootstrap-turn` that can choose between posture inspection, repair,
  or bootstrap grounding for common agent turns
- when Odylith cannot narrow the slice, print the exact next fallback command
  instead of only implying that raw repo scan is now required

### Wave 2: Progress, preview, and mutation-scope clarity
- add step-by-step progress, heartbeats, and final status summaries for
  `install`, `sync`, and Atlas/Mermaid refresh paths
- add dry-run and mutation preview so Odylith can say exactly which managed
  files, generated surfaces, and repo-owned truth it will rewrite before it
  mutates tracked files
- make dirty-worktree behavior explicit: guidance-only refresh, generated
  surface refresh, and repo-owned governance truth refresh should be
  distinguishable before execution

### Wave 3: Recovery, refresh, and status contract polish
- keep surface-scoped refresh narrow and explicit so “refresh dashboard” does
  not trigger Atlas/Mermaid or broader governance churn unless requested
- keep reinstall semantics one-step and unambiguous for active runtime plus
  tracked pin adoption
- make missing-launcher recovery first-class from the consumer repo itself
- make `odylith version` and related status readouts say plainly that Odylith
  uses managed Python while repo code still validates on the project toolchain
- keep installed skills, help text, and guides atomically aligned with the
  shipped CLI contract

## Scope
- release-facing operator UX and command-surface clarity only
- smart first-turn routing and explicit fallback guidance
- progress, heartbeat, dry-run, and mutation-preview behavior for the highest
  friction lifecycle commands
- refresh-scope, recovery, interpreter/status, and docs/help discipline for
  the shipped release contract

## Non-Goals
- redesigning the underlying managed-runtime architecture
- replacing Odylith's fail-closed widening behavior with speculative scan
  automation
- forcing all of these improvements into one implementation PR without clear
  execution waves

## Risks
- a “smart start” command could become opaque if it hides too much decision
  logic from operators
- preview and progress layers could drift from actual mutation behavior if they
  are bolted on instead of sourced from the same execution plan
- trying to land every item in one slice would blur scope ownership and
  validation responsibilities

## Dependencies
- `B-027` clarified runtime, write, and validation boundaries
- `B-030` established recovery, reinstall, and dashboard-refresh hardening
- `B-031` established short-form first-turn grounding commands

## Success Metrics
- common agent turns have one obvious supported first command
- long-running Odylith commands show enough progress to avoid looking hung
- dry-run output names the exact mutation set before tracked files change
- refresh scope is narrow and legible by default
- missing-launcher recovery is obvious from the consumer repo itself
- `version` and fallback guidance read clearly enough that users do not infer
  the wrong runtime or validation model
- installed docs, help text, and skills match the actual shipped command
  contract

## Validation
- focused CLI, install, runtime, and Atlas regression coverage for each wave
- browser proof where progress and refresh UX surfaces are user-visible
- `git diff --check`

## Rollout
Promote this umbrella to one active technical plan and execute it as bounded
waves inside the same release contract. Use the existing `B-030`, `B-031`, and
boundary-clarity work as the foundation instead of opening new child
workstreams unless a later wave genuinely outgrows this boundary.

## Why Now
Odylith is close enough that the next bottleneck is no longer raw capability.
It is whether the release feels explicit, trustworthy, and low-friction at the
moment an operator or agent reaches for it.

## Product View
Odylith should feel like a product with a point of view, not a clever pile of
verbs. The next release needs to make the right first move, the mutation scope,
and the recovery path obvious.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `dashboard`
- `atlas`
- `release`

## Interface Changes
- the next release should converge on one explicit agent-first turn-start path
- lifecycle commands should show progress and preview what they will mutate
- refresh, recovery, and status commands should expose scope and toolchain
  boundaries more plainly

## Migration/Compatibility
- expected to be additive and contract-tightening
- existing install/runtime state should remain compatible
- some guidance and help text will need synchronized bundle refresh to stay in
  lockstep with the CLI

## Test Strategy
- prove each wave separately rather than waiting for a full umbrella landing
- keep validation tied to the affected command surface and surfaced UX
- fail closed if help text or shipped skill/docs drift from the real CLI flags

## Open Questions
- whether the smart first-turn command should remain explicit about its chosen
  lane, for example `status`, `repair`, or `bootstrap`, in the final output
- whether mutation preview should be available as a generic `--dry-run`
  contract across multiple commands or through dedicated preview subcommands

## Outcome
- Landed on 2026-03-30 with the bound B-032 technical plan closed to `done`.
- `odylith start` is now the canonical first-turn command, lifecycle and
  refresh commands expose shared `--dry-run` previews, long-running sync and
  Atlas paths emit progress plus heartbeat-backed status, and narrowing
  guidance now prints exact fallback commands instead of vague widening hints.
