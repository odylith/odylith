Status: In progress

Created: 2026-04-11

Updated: 2026-04-11

Backlog: B-085

Goal: Bake the Claude host surface logic (statusline and PreCompact
snapshot, with room for future Claude host surfaces) into `src/odylith/`
as first-class Python modules under `runtime/surfaces/`, expose them
through a thin `odylith claude` CLI subcommand group, and leave only
one-line exec shims under `.claude/`. B-084 paused mid-slice once the
operator pointed out that the in-progress Claude host surface work was
landing as external shell and standalone-Python files under `.claude/`
instead of as first-class Python alongside every other product surface.
B-085 is the bounded child slice that makes the architectural pivot real
without touching any Claude host logic in `cli.py` beyond a minimal
dispatcher.

Assumptions:
- `src/odylith/runtime/surfaces/` is the right neighborhood for the new
  modules, because every other rendered-state-to-surface file already
  lives there (`compass_standup_brief_narrator.py`, `render_compass_dashboard.py`,
  `dashboard_shell_links.py`, the tooling presenters). Flat files with a
  `claude_host_` prefix matches the existing taxonomy instead of inventing
  a new `hosts/` subtree.
- `src/odylith/cli.py` is already 2161 LOC, deep in the repo's red zone.
  Additions must be minimal and strictly dispatch-shaped; any substantive
  logic belongs in the new module.
- `.claude/` remains declarative and small: exec shims, JSON settings,
  subagent frontmatter, and slash commands - not inline Python or bash
  rendering logic.
- Claude Code swallows statusline errors silently, so the statusline render
  path must return a safe fallback string on any error instead of raising.

Constraints:
- Do not grow `src/odylith/cli.py` beyond a dispatcher scaffold for the new
  subcommand group. Any Claude host surface logic must live in the new
  `surfaces/claude_host_*.py` modules.
- Do not reintroduce inline Python inside `.claude/statusline.sh`. The shim
  must be a one-liner that execs the CLI subcommand.
- Do not add a standalone `.claude/hooks/pre-compact-snapshot.py` script.
  The PreCompact hook entry must call the CLI subcommand directly.
- Do not regress the existing `.claude/hooks/*` behavior the repo already
  ships; those files are out of scope for this slice.
- The new subcommand group must not fail closed when Compass runtime state
  is partial or missing; it must degrade to a clearly-marked safe fallback.

Reversibility: The architectural pivot is reversible. If the new module
pattern turns out to be a poor fit we can collapse the new surfaces back
into `.claude/` scripts and drop the `claude` subcommand group. The
characterization test coverage for the new modules pins the current
expected behavior so a later refactor is legible.

Boundary Conditions:
- Scope includes `src/odylith/runtime/surfaces/claude_host_statusline.py`,
  `src/odylith/runtime/surfaces/claude_host_precompact_snapshot.py`, a thin
  `claude` subcommand dispatcher in `src/odylith/cli.py`, the two matching
  `tests/unit/runtime/test_claude_host_*.py` files, the one-line
  `.claude/statusline.sh` exec shim, the `.claude/settings.json` statusLine
  wiring, and the PreCompact hook registration. Governance trail: this
  technical plan, B-085 Radar idea, Compass log.
- Scope excludes refactoring the existing `.claude/hooks/*` Python files
  into `src/odylith/`, decomposing `cli.py`, adding `.claude/mcp/` surfaces,
  and fresh Claude host benchmark proof.

Related Bugs:
- No new Casebook bug is opened for this slice because the architectural
  drift was caught in implementation before it shipped. CB-103 remains the
  parent-slice bug record for the silent model-selection flag regression.

## Learnings
- [x] External shell + inline Python adapters under `.claude/` are the
      wrong shape for Odylith product surfaces. Every other rendered-state
      surface lives in `src/odylith/runtime/surfaces/` as a flat Python
      module with prefix grouping. The Claude host surface should not be
      a parallel script lane; it should be the same shape as the rest.
- [x] When `cli.py` is already in the red-zone file-size tier, new
      subcommand groups must land as minimal dispatchers that delegate to
      a new module, not as inline logic growth. The dispatcher pattern
      keeps the red-zone file from getting worse while still exposing the
      new capability through the canonical CLI surface.
- [x] In the Odylith product repo, `_sync_managed_project_claude_assets`
      is guarded by an early-return for `PRODUCT_REPO_ROLE`, so the live
      `.claude/` tree is hand-edited and never overwritten by `odylith
      sync`. Bundle-asset edits under
      `src/odylith/bundle/assets/project-root/.claude/` are the
      consumer-lane vehicle and must be kept in lockstep with the live
      `.claude/` copies for the next release to carry the change forward
      coherently.
- [x] The Claude Code statusline contract expects a single-line string on
      stdout and swallows stderr silently. The render path must never
      raise, and the shim must translate any non-zero CLI exit into the
      canonical `Odylith · grounding unavailable` fallback so dogfood
      maintainers on a behind-pinned runtime see an honest signal
      instead of a broken statusline.

## Must-Ship
- [x] File the B-085 Radar idea and this technical plan before any code
      moves (governance-first invariant).
- [x] Create `src/odylith/runtime/surfaces/claude_host_statusline.py` with
      a `render_claude_host_statusline(...)` entry point that reads
      `odylith/compass/runtime/current.v1.json` and the governed brief and
      returns a compact status string.
- [x] Create `src/odylith/runtime/surfaces/claude_host_precompact_snapshot.py`
      with a `write_claude_host_precompact_snapshot(...)` entry point that
      captures the active Odylith slice to Claude's project auto-memory
      directory.
- [x] Both modules degrade to a clearly-marked safe fallback on missing or
      partial Compass runtime state instead of raising. Shared helpers
      live in `src/odylith/runtime/surfaces/claude_host_shared.py` so the
      two surface modules do not duplicate project-slug, Compass-runtime,
      freshness-label, or host-family-detection logic.
- [x] Add a thin `claude` subcommand dispatcher to `src/odylith/cli.py`
      via `_CLAUDE_HOST_COMMAND_MODULES` path constants, thin
      `_cmd_claude_*` dispatcher functions that call `_run_module_main`,
      a fast-path branch in `main()`, and parser wiring under the
      `claude` subparser. `cli.py` grows only by dispatcher scaffolding;
      no Claude host logic lands inline.
- [x] Replace `.claude/statusline.sh` with a one-line exec shim that
      delegates to `./.odylith/bin/odylith claude statusline` and falls
      back to `Odylith · grounding unavailable` on any non-zero exit.
- [x] Wire `.claude/settings.json` `statusLine` to the shim (live and
      bundle-asset copies).
- [x] Register a `PreCompact` hook in `.claude/settings.json` that calls
      `./.odylith/bin/odylith claude pre-compact-snapshot --quiet`
      directly (live and bundle-asset copies).
- [x] Add `tests/unit/runtime/test_claude_host_statusline.py` covering
      nominal render, missing Compass state, malformed snapshot, and the
      safe fallback path (8 tests green).
- [x] Add `tests/unit/runtime/test_claude_host_precompact_snapshot.py`
      covering successful snapshot write, missing target directory,
      missing Compass state, and idempotent re-run (10 tests green).
- [x] Log the slice to Compass so the next standup brief surfaces the new
      Claude host surface module posture.

## Should-Ship
- [x] Brief inline comment in the statusline module that documents the
      Claude Code silent-error behavior, so the next maintainer knows why
      the module never raises from the render path.

## Defer
- [ ] Bake-in of the existing `.claude/hooks/session-start-ground.py`,
      `subagent-start-ground.py`, `user-prompt-context.py`,
      `guard-destructive-bash.py`, `refresh-governance-after-edit.py`,
      `log-subagent-stop.py`, and `log-stop-summary.py` scripts. Each of
      those is a separate bounded bake-in slice if the operator wants them
      moved later.
- [ ] Decomposing `src/odylith/cli.py` toward the 1200 LOC hard limit;
      that is a separate governance slice.
- [ ] `.claude/mcp/` surfaces. Out of scope per operator direction on the
      B-084 parent.

## Success Criteria
- [x] `./.odylith/bin/odylith claude statusline` returns a compact governed
      status string from real Compass runtime state (smoke-tested live,
      returns `Odylith · B-005 · brief 7h · host claude` against the
      current repo state).
- [x] `./.odylith/bin/odylith claude pre-compact-snapshot` writes the
      active Odylith slice to Claude's project auto-memory directory
      (smoke-tested live, wrote
      `~/.claude/projects/-Users-freedom-code-odylith/memory/odylith-precompact-snapshot.md`).
- [x] `.claude/statusline.sh` is a short exec shim with no inline
      rendering logic.
- [x] `.claude/settings.json` carries both the statusLine wiring and the
      PreCompact hook registration.
- [x] `tests/unit/runtime/test_claude_host_statusline.py` and
      `tests/unit/runtime/test_claude_host_precompact_snapshot.py` run
      green in the same harness as the other surface tests.
- [x] `src/odylith/cli.py` LOC growth is bounded to dispatcher scaffolding
      only (no inlined Claude host logic).

## Non-Goals
- [ ] Refactoring the existing `.claude/hooks/*` Python files into
      `src/odylith/`.
- [ ] Growing `cli.py` with inline Claude host logic.
- [ ] Decomposing `cli.py` toward the 1200 LOC hard limit.
- [ ] Adding `.claude/mcp/` surfaces.
- [ ] Fresh benchmark proof for the Claude host surface.

## Impacted Areas
- [x] [2026-04-11-claude-host-python-surface-bake-statusline-and-precompact-snapshot.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-11-claude-host-python-surface-bake-statusline-and-precompact-snapshot.md)
- [x] [2026-04-11-claude-host-python-surface-bake-statusline-and-precompact-snapshot.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-11-claude-host-python-surface-bake-statusline-and-precompact-snapshot.md)
- [x] [src/odylith/runtime/surfaces/claude_host_shared.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/claude_host_shared.py)
- [x] [src/odylith/runtime/surfaces/claude_host_statusline.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/claude_host_statusline.py)
- [x] [src/odylith/runtime/surfaces/claude_host_precompact_snapshot.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/claude_host_precompact_snapshot.py)
- [x] [src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [.claude/statusline.sh](/Users/freedom/code/odylith/.claude/statusline.sh)
- [x] [.claude/settings.json](/Users/freedom/code/odylith/.claude/settings.json)
- [x] [src/odylith/bundle/assets/project-root/.claude/statusline.sh](/Users/freedom/code/odylith/src/odylith/bundle/assets/project-root/.claude/statusline.sh)
- [x] [src/odylith/bundle/assets/project-root/.claude/settings.json](/Users/freedom/code/odylith/src/odylith/bundle/assets/project-root/.claude/settings.json)
- [x] [tests/unit/runtime/test_claude_host_statusline.py](/Users/freedom/code/odylith/tests/unit/runtime/test_claude_host_statusline.py)
- [x] [tests/unit/runtime/test_claude_host_precompact_snapshot.py](/Users/freedom/code/odylith/tests/unit/runtime/test_claude_host_precompact_snapshot.py)

## Rollout
1. Land this plan and the B-085 Radar idea first (governance before code).
2. Create the two new `surfaces/claude_host_*.py` modules and their unit
   test coverage. Green-test locally.
3. Add the thin `claude` subcommand group to `cli.py` as a minimal
   dispatcher that delegates to the two modules.
4. Replace the transient `.claude/statusline.sh` with the one-line exec
   shim and wire the `statusLine` entry plus the `PreCompact` hook in
   `.claude/settings.json`.
5. Run the validation step, refresh governed surfaces, and log the slice
   to Compass.

## Cross-Lane Impact
This slice ships visible Claude Code surface wiring alongside unreleased
`src/odylith/cli.py` dispatcher code, so each lane has a different
transitional posture until the next pinned runtime release carries the
change set forward:
- **dev-maintainer (detached `source-local`)**: fully live. The shim,
  settings wiring, and `odylith claude ...` subcommand all resolve
  against the live unreleased `src/odylith/runtime/surfaces/claude_host_*`
  modules. No transient state. This is the posture that validated the
  slice end-to-end.
- **pinned dogfood**: transiently degraded until the pinned runtime is
  rebuilt or the next maintainer release lands. The hand-edited
  `.claude/settings.json` and `.claude/statusline.sh` in the product
  repo are not overwritten by `odylith sync` (the
  `_sync_managed_project_claude_assets` helper is guarded by the
  `PRODUCT_REPO_ROLE` early-return), so Claude Code in dogfood posture
  will still try to invoke `./.odylith/bin/odylith claude statusline`.
  The pinned runtime answers with "unknown subcommand: claude", the
  shim catches the non-zero exit, and Claude Code renders the safe
  fallback `Odylith · grounding unavailable`. The `PreCompact` hook
  similarly errors and Claude Code logs the hook failure as
  best-effort; compaction itself still proceeds. This is expected
  transient state. It self-corrects the moment the pinned runtime is
  rebuilt at or after the commit that introduces the `claude`
  subcommand.
- **consumer (pinned)**: coherent at the next Odylith release. The
  bundle asset copies under `src/odylith/bundle/assets/project-root/.claude/`
  ship together with the pinned runtime that knows the `claude`
  subcommand, so consumer upgrades flip atomically between both sides.
  Consumer repos without a prior Compass runtime snapshot degrade to
  `Odylith · no active workstream · brief no snapshot · host claude`,
  which is correct and is covered by the unit test harness for the
  new modules.

The transient-state decision recorded against this slice is
**option 3 / ship-now-with-documentation**: land the wiring alongside
the dispatcher so dev-maintainer and consumer lanes stay consistent,
accept the dogfood degraded-statusline signal as honest operator
feedback, and rely on the next pinned runtime rebuild to close the
window. Do not silence the fallback string; `Odylith · grounding
unavailable` is the intended dogfood read when the pinned runtime is
behind the live `.claude/` wiring.

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_claude_host_statusline.py tests/unit/runtime/test_claude_host_precompact_snapshot.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_claude_project_hooks.py`
- [ ] `./.odylith/bin/odylith claude statusline --repo-root .` smoke test
- [ ] `./.odylith/bin/odylith sync --repo-root . --check-only`
- [ ] `git diff --check`

## Outcome Snapshot
- [ ] The Claude host surface lives in `src/odylith/runtime/surfaces/` as
      first-class Python, runs through the `odylith claude` CLI subcommand
      group, and is covered by the same unit test harness as every other
      product surface.
- [ ] `.claude/` stays declarative: statusline and PreCompact entries are
      short exec shims that point at the governed CLI subcommand.
- [ ] `src/odylith/cli.py` gains only a dispatcher scaffold; the red-zone
      file-size posture does not get worse, and the decomposition
      workstream for `cli.py` remains open and untouched.
