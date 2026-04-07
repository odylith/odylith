# Delivery Governance Surface Ops

Use this skill for substantive grounded repo work when Odylith should keep backlog, plans, components, Atlas, Casebook, Compass, and closeout truth synchronized automatically.

## Lane Boundary
- Consumer lane:
  - use `./.odylith/bin/odylith` for Odylith commands
  - validate repo code with the consumer repo's own toolchain
- Product-repo maintainer mode:
  - pinned dogfood posture proves the shipped runtime
  - detached `source-local` posture is the explicit live-source dev lane
- Interpreter choice does not control which repo files the agent may edit.

## Default Flow
- ground the slice through Odylith packets first
- keep commentary focused on the slice, the repo truth, and the validation plan; avoid narrating startup, routing, or degraded-attempt internals unless the user needs a command or a blocker explanation
- keep Odylith ambient by default during work; weave grounded governance facts into ordinary updates and only emit explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` lines when they materially change the next move
- when closeout would benefit from naming Odylith, use at most one short `Odylith Assist:` line; prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance ids inline when they were actually changed, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and back it with concrete observed counts, measured deltas, or validation outcomes while keeping it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Silence is better than filler.
- search existing workstream, plan, bug, component, diagram, and session or Compass context before writing
- extend, consolidate, or reopen existing truth before creating new governed records
- create a missing workstream and bound plan before non-trivial implementation when the slice is genuinely new
- add child workstreams or execution waves when the slice is truly umbrella-shaped
- suggest or deepen Registry components and living specs when new or clarified system boundaries appear
- update or create Atlas coverage when a materially changed flow, seam, or contract lacks truthful diagrams
- run Casebook preflight and capture named failures or repeat-debug loops in the same turn
- keep Compass updates intent-first and carry forward constraints plus validation obligations
- keep closeout surfaces explicit
- prefer proof bundles over prose summaries
- fail closed when the evidence is incomplete
- use strict refresh and strict check intentionally, not interchangeably

## Canonical Commands

```bash
./.odylith/bin/odylith context-engine --repo-root . governance-slice --working-tree
./.odylith/bin/odylith sync --repo-root .
./.odylith/bin/odylith dashboard refresh --repo-root .
./.odylith/bin/odylith dashboard refresh --repo-root . --surfaces shell,radar,compass
./.odylith/bin/odylith dashboard refresh --repo-root . --surfaces atlas --atlas-sync
./.odylith/bin/odylith sync --repo-root . --force --impact-mode full --check-clean
./.odylith/bin/odylith sync --repo-root . --check-only --check-clean --runtime-mode standalone
./.odylith/bin/odylith validate plan-traceability --repo-root .
./.odylith/bin/odylith validate plan-risk-mitigation --repo-root .
./.odylith/bin/odylith atlas auto-update --repo-root . --from-git-working-tree --fail-on-stale
./.odylith/bin/odylith atlas render --repo-root . --fail-on-stale
./.odylith/bin/odylith compass log --repo-root . --kind implementation --summary "<intent-first update>"
./.odylith/bin/odylith compass watch-transactions --repo-root . --interval-seconds 15
```

## Rules

- Treat this skill as Odylith's governance-autopilot loop, not as optional closeout polish.
- `dashboard refresh --repo-root .` is the low-friction render-only refresh path when you need the shell current without running the full governance pipeline. It refreshes `tooling_shell`, `radar`, and `compass` by default, prints the included and excluded surfaces, and points at `--surfaces atlas --atlas-sync` when Atlas is stale but excluded.
- `sync --force --impact-mode full --check-clean` is the authoritative write-mode refresh gate.
- `sync --check-only --check-clean --runtime-mode standalone` is the authoritative non-mutating clean proof lane.
- Refresh and shell upkeep must stay local and deterministic when the Tribunal reasoning artifact is absent; do not wait on opportunistic provider enrichment just to refresh governed surfaces.
- If explicit Tribunal provider enrichment times out during a run, keep the remaining cases deterministic instead of retrying the same unhealthy provider path across the whole queue.
- If strict sync is blocked only by Mermaid freshness, repair Atlas first, rerender, then rerun the strict gate.
