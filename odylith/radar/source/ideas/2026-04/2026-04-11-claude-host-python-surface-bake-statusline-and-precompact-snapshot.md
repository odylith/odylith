---
status: implementation
idea_id: B-085
title: Claude Host Python Surface Bake - Statusline, PreCompact Snapshot, and CLI Subcommand
date: 2026-04-11
priority: P0
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: Odylith Claude host surface runtime, `odylith claude` CLI subcommand group, `.claude/statusline.sh` exec shim, `.claude/settings.json` statusLine and PreCompact wiring, runtime surfaces module layout, Claude host test coverage
sizing: S
complexity: Medium
ordering_score: 100
ordering_rationale: B-084 paused mid-slice once the operator observed that the Claude statusline, PreCompact snapshot, and other host adapters were being added as external shell or standalone-Python shims under `.claude/` instead of being baked into the Odylith Python codebase like every other product surface. This child slice moves the Claude host surface logic into `src/odylith/runtime/surfaces/` as first-class Python modules, exposes them through a thin `odylith claude` CLI subcommand group, and keeps the `.claude/` entries as one-line exec shims.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-11-claude-host-python-surface-bake-statusline-and-precompact-snapshot.md
execution_model: standard
workstream_type: child
workstream_parent: B-084
workstream_children:
workstream_depends_on: B-084
workstream_blocks:
related_diagram_ids: D-030
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
During B-084 implementation the operator pointed out an architectural drift:
the Claude host surface expansion was being landed as external shell and
standalone-Python files under `.claude/` (a `statusline.sh` bash shim reading
the governed brief via inline Python, a separate `pre-compact-snapshot.py`
hook script, and a trajectory toward more such ad-hoc adapters), instead of
being baked into the Odylith Python codebase like every other product
surface. The consequence is threefold:

- The logic that reads Compass runtime state, renders a compact statusline
  string, and writes a PreCompact snapshot is invisible to the Odylith test
  harness and cannot be unit-tested alongside the rest of the runtime
  surfaces.
- The same compact-state rendering code lives outside `src/odylith/` and
  therefore is not governed by the repo's own file-size discipline,
  refactor-first posture, or release contract.
- Future Claude host surface growth (hooks, skills, memory bridges, MCP
  adapters when they come back on scope) would keep accumulating as
  external scripts instead of as a cohesive Claude host module, which is the
  exact same drift `CB-084` closed for Codex-only policy leaks in shared
  runtime surfaces.

The operator explicitly chose "First-class `src/odylith/` module" for the
architecture and "Revert and bake in Python" for the statusline. B-084 does
not capture this architectural pivot; it predates it. B-085 is the bounded
child slice that makes the pivot real.

## Customer
- Primary: operators who run Odylith under Claude Code and want the
  statusline, PreCompact snapshot, and other Claude host surfaces to work
  exactly like the Codex-side Compass surfaces (governed, Python, tested,
  versioned).
- Secondary: Odylith maintainers who need the Claude host surface code to
  be part of the Odylith runtime they already ship, test, and refactor
  under repo file-size discipline, not a parallel `.claude/` script lane.

## Opportunity
Bake every Claude host surface into `src/odylith/runtime/surfaces/` as
first-class Python modules with prefix grouping (`claude_host_*.py`), expose
them through a thin `odylith claude` CLI subcommand dispatcher that delegates
to the new modules, and leave only one-line `exec` shims and hook entries
under `.claude/`. That keeps the Odylith Python codebase authoritative for
the Claude host surface, while `.claude/` stays declarative and small.

## Proposed Solution
- add `src/odylith/runtime/surfaces/claude_host_statusline.py` that reads
  `odylith/compass/runtime/current.v1.json` and the governed brief and
  returns the compact status string
- add `src/odylith/runtime/surfaces/claude_host_precompact_snapshot.py` that
  captures the active Odylith slice (workstream, component, brief freshness,
  recent execution events) into Claude's project auto-memory directory on
  PreCompact events
- add a thin `claude` subcommand group to `src/odylith/cli.py` that imports
  and delegates to the new modules through the existing lazy-import module
  pattern, keeping `cli.py` additions minimal because the file is already
  in the >2000 LOC red zone
- replace the transient `.claude/statusline.sh` with a one-line exec shim
  (`exec "$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude statusline "$@"`)
- wire `.claude/settings.json` `statusLine` to the shim and register a
  `PreCompact` hook that calls `./.odylith/bin/odylith claude pre-compact-snapshot`
  directly, with no intermediate `.claude/hooks/*.py` script
- add `tests/unit/runtime/test_claude_host_statusline.py` and
  `tests/unit/runtime/test_claude_host_precompact_snapshot.py` alongside the
  existing `test_compass_*` surface tests so the Claude host surface runs
  in the same harness
- keep the `.claude/settings.json` allowlist for `./.odylith/bin/odylith
  claude:*` already added in B-084 so the new subcommand group is pre-approved

## Scope
- `src/odylith/runtime/surfaces/claude_host_statusline.py` (new, flat file)
- `src/odylith/runtime/surfaces/claude_host_precompact_snapshot.py` (new)
- `src/odylith/cli.py` (thin dispatcher addition only; no logic growth)
- `.claude/statusline.sh` (one-line exec shim)
- `.claude/settings.json` (statusLine wiring, PreCompact hook registration)
- `tests/unit/runtime/test_claude_host_statusline.py` (new)
- `tests/unit/runtime/test_claude_host_precompact_snapshot.py` (new)
- governance trail: this Radar idea, the B-085 technical plan, Compass log

## Non-Goals
- Refactoring or extending other existing `.claude/hooks/*.py` files that
  already live under `.claude/hooks/` from earlier slices; those are a
  separate bake-in workstream if the operator later wants them moved
- Refactoring `src/odylith/cli.py` to bring it under the 1200 LOC hard
  limit; the file is in the red zone but its decomposition is a separate
  governance slice and out of scope here
- Adding an MCP server surface; MCP remains out of scope per operator
  direction on the B-084 parent
- Fresh benchmark proof for the Claude host surface; this slice is
  structural re-layout, not measured proof

## Risks
- `src/odylith/cli.py` is already over the 2000 LOC red-zone threshold for
  hand-maintained source files. The `claude` subcommand group must land as
  a minimal dispatcher (module path constant plus a small `_handle_claude_*`
  function that delegates to the new surfaces module), not as inline logic
  growth. Adding substantive Claude host logic directly into `cli.py` would
  make the file-size drift worse and violate the repo's refactor-first
  posture
- Moving the statusline logic from an external bash+inline-Python shim to a
  real Python module changes the failure mode: a missing Compass runtime
  file should now degrade to a clearly-marked fallback string instead of
  raising inside the statusline render path, because Claude Code swallows
  statusline errors silently
- The PreCompact hook fires on a documented Claude Code event; if the hook
  command returns a non-zero exit or takes too long, Claude's compaction
  may proceed without the snapshot being written. The new module must be
  fast and resilient, and the `.claude/settings.json` timeout must be set
  generously

## Dependencies
- B-084 (direct parent) supplies the Claude host capability contract, the
  `(host_family, profile) -> (model, reasoning_effort)` ladder, and the
  `.claude/` project surface expansion that the statusline and PreCompact
  snapshot render into
- CB-103 is the parent slice's bug record; this child slice does not open a
  new Casebook bug because the drift was caught in implementation, not in
  shipped behavior

## Success Metrics
- `./.odylith/bin/odylith claude statusline` returns a compact governed
  status string with the active workstream, brief freshness, and provider
  posture, reading real Compass runtime state
- `./.odylith/bin/odylith claude pre-compact-snapshot` writes the active
  Odylith slice to Claude's project auto-memory directory without raising
  on missing state
- `.claude/statusline.sh` is a one-line exec shim with no inline Python or
  pipe logic
- `.claude/settings.json` wires both the statusLine and the PreCompact hook
  to the new CLI subcommand; the existing permissions allowlist for
  `./.odylith/bin/odylith claude:*` is respected
- `tests/unit/runtime/test_claude_host_statusline.py` and
  `tests/unit/runtime/test_claude_host_precompact_snapshot.py` run green in
  the same harness as the other surface tests
- `src/odylith/cli.py` LOC growth is bounded to the dispatcher scaffolding
  only; no Claude host logic is inlined

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_claude_host_statusline.py tests/unit/runtime/test_claude_host_precompact_snapshot.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/test_claude_project_hooks.py`
- `./.odylith/bin/odylith claude statusline --repo-root .` smoke test
- `./.odylith/bin/odylith sync --repo-root . --check-only`
- `git diff --check`

## Rollout
1. Land this Radar idea and the matching technical plan first so the child
   slice is governed before code moves.
2. Add the two new `surfaces/claude_host_*.py` modules with their unit test
   coverage.
3. Add the thin `claude` subcommand dispatcher to `cli.py` pointing at the
   new modules.
4. Replace `.claude/statusline.sh` with the one-line exec shim and wire the
   `statusLine` entry plus the `PreCompact` hook in `.claude/settings.json`.
5. Run the full validation step and log the slice to Compass.

## Why Now
The Claude host surface expansion is actively landing inside B-084. If the
statusline and PreCompact surfaces land as external shell and standalone
Python files, the next Claude host surface change will have to either
duplicate the ad-hoc pattern or reverse it, which is more expensive than
paying for the correct layout once.

## Product View
Every Odylith product surface - dashboards, compass brief renderers, shell
onboarding, tooling presenters - is Python under `src/odylith/runtime/`.
The Claude host surface should be the same shape, not a parallel
`.claude/` script lane.

## Impacted Components
- `odylith`
- `execution-governance`

## Interface Changes
- new `odylith claude` CLI subcommand group with `statusline` and
  `pre-compact-snapshot` subcommands
- new `src/odylith/runtime/surfaces/claude_host_statusline.py` entry point
- new `src/odylith/runtime/surfaces/claude_host_precompact_snapshot.py`
  entry point
- `.claude/statusline.sh` becomes a one-line exec shim

## Migration/Compatibility
- Codex callers see no diff; the new subcommand group is Claude host only
- `.claude/` remains backward compatible because the surface additions are
  additive; repos that do not opt in to the statusLine or PreCompact wiring
  still work

## Test Strategy
- Unit coverage for the two new surfaces modules using fake Compass runtime
  state fixtures, modeled after the existing `test_compass_*` surface tests
- Reuse the `_write_fake_launcher` harness shape from
  `tests/unit/test_claude_project_hooks.py` where the PreCompact snapshot
  needs to call out to the launcher

## Open Questions
- Whether the PreCompact snapshot should also include the last-N Compass
  timeline events, or just the active slice; deferred to implementation
  time based on how large the snapshot payload becomes
