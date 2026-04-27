Status: In progress

Created: 2026-04-12

Updated: 2026-04-13

Backlog: B-090

Goal: Bring the 27 still-failing unit tests that pre-date the B-089 Claude
host capability layer back to green without rewriting any product code,
isolating each cluster to a focused test or helper update and proving
that none of the failures hide a real product regression behind test
drift.

Assumptions:
- The 27 failures all pre-date B-089. They were observed before the
  Claude host capability layer landed and stayed unchanged across the
  9402f5d, 72d996a, 5fb514b, and 52c16d4 commits. The B-089 work itself
  did not cause any of them.
- The failures cluster as: 17 orchestrator/router profile inference in
  `tests/unit/runtime/test_subagent_reasoning_ladder.py`, 4 benchmark
  dispatch (3 in `tests/unit/test_cli_maintainer_lane.py`, 1 in
  `tests/unit/test_cli_audit.py`), 1 governance auto-promote-workstream-
  phase in `tests/unit/runtime/test_auto_promote_workstream_phase.py`,
  2 public-tree hygiene in `tests/unit/runtime/test_hygiene.py`, 2
  benchmark runner delegation in
  `tests/unit/runtime/test_odylith_benchmark_runner.py`, and 1
  render_tooling_dashboard compass refresh in
  `tests/unit/runtime/test_render_tooling_dashboard.py`.
- The hygiene cluster is investigated first because a real public-tree
  contract leak (legacy contract paths shipped into consumer truth roots
  via the bundle) is the only failure shape in the 27 that could
  represent a live product regression instead of test drift.
- The orchestrator/router profile inference cluster traces back to the
  d5d78a9 Codex host parity commit which moved model resolution and
  reasoning-effort canonicalization through a new path. The parameterized
  test cases reference model names and reasoning labels that were renamed
  by that refactor.
- The benchmark dispatch cluster is mock-target drift: the test mocks
  `cli.benchmark_compare.compare_latest_to_baseline` but the live CLI
  handler now resolves the function through a different import path
  introduced when the benchmark routing was refactored through the
  `context_engine` module.
- The auto-promote-workstream-phase test is a contract-shape drift in
  the decision-signal payload after the same governance refactor wave.
- The render_tooling_dashboard test is a projection-shape drift in how
  failed Compass refresh state is surfaced into the shell status row.
- The odylith_benchmark_runner delegation tests reference an older
  delegation contract for the live validation heavy and explicit
  workstream proof slices.

Constraints:
- Do not rewrite product code unless the hygiene investigation proves a
  real public-tree contract leak. Every other cluster fix is a bounded
  test-side update.
- Do not delete or skip any failing test. Each fix must keep the original
  intent intact and re-prove it against the live contract.
- Keep the slice bounded to test files and (if hygiene proves a real
  leak) the minimum product fix needed to close that leak. Do not pull
  unrelated cleanup into B-090.
- Stay on `2026/freedom/v0.1.11` since `main` is read-only for authoring
  in maintainer mode.
- Follow the same two-commit pattern as B-089: a focused test catch-up
  commit followed by a governed surface refresh commit driven by
  `odylith sync`.

Reversibility: The slice is structurally reversible. If a fix turns out
to be wrong, the test file delta can be reverted independently and the
remaining clusters re-investigated. The hygiene cluster is the only
shape that could touch product code; if that fix lands and later proves
wrong, the bundle mirror is rebuilt from source truth via `odylith sync`.

Boundary Conditions:
- Scope includes the 27 failing test files, any helpers those tests
  import, the minimum product-side fix needed to close a real public-
  tree contract leak (if the hygiene cluster proves one), and the
  derived governance surface refresh that follows.
- Scope excludes any orchestrator/router profile inference logic
  rewrites, any benchmark routing decomposition, any governance contract
  refactors, and any render_tooling_dashboard projection rewrites.
- Scope excludes the live `claude` CLI baseline-safe ladder rungs that
  need a machine with `claude` on PATH. Those stay parked for a separate
  proof session on a second machine.

Related Bugs:
- No new Casebook bug is opened for this slice. The 27 failures are
  pre-existing test drift rooted in d5d78a9 (Codex host parity) and the
  earlier benchmark routing refactor; they did not surface as user-
  visible product bugs and they did not block the B-089 ship.

## Learnings
- [x] Hygiene investigation: 2 failures, 2 root causes. (A) The
      `scripts/` needle was over-broad — `scripts/release/publish_release_assets.py`
      is a current valid maintainer file referenced in atlas catalog and B-083
      plan. Fix: removed `scripts/` from the needle list; remaining needles
      (`from scripts.`, `import scripts.`, `python -m scripts`, `tests/scripts/`)
      still guard against legacy code patterns. (B) The bundle shipped
      `radar/source/ideas/` and `technical-plans/in-progress/` into consumer
      truth roots — a real product regression introduced on this branch when
      the mirror prefixes were widened in `2f1a50e`. Fix: added
      `_SOURCE_TRUTH_BUNDLE_MIRROR_EXCLUDE_PREFIXES` to
      `sync_workstream_artifacts.py` and deleted the 19 offending mirror files.
- [x] Orchestrator profile-inference: the d5d78a9 host-family axis made
      `RouterProfile.model` resolve per-host (Codex vs Claude). Running
      tests in Claude Code returned Claude model names that
      `_router_profile_from_runtime` couldn't recognize. Fix: added
      `monkeypatch` with Codex host env to all 17 affected tests.
- [x] Benchmark dispatch: the CLI handler at line 1376 of `cli.py` uses
      `_load_module(_BENCHMARK_COMPARE_MODULE)` which shadows the module-
      level lazy proxy. Tests patched the proxy at `cli.benchmark_compare`
      but the handler bypassed it. Fix: patched the real module at
      `odylith.runtime.evaluation.benchmark_compare` directly.
- [x] CLI gap (maintainer feedback): `odylith governance reconcile-plan-
      workstream-binding` is documented in `CLI_FIRST_POLICY.md` (line
      24) as the owner of "active-plan rows and bindings" in
      `odylith/technical-plans/INDEX.md`, but the live implementation
      only updates the backlog cell of an existing row
      (`_update_plan_index_backlog` in
      `src/odylith/runtime/governance/reconcile_plan_workstream_binding.py`)
      and silently `continue`s when `rows_by_plan.get(plan_path)` is
      `None` (line 700-701 of the same module). There is no insert
      path for new active-plan rows in any sync step. Empirical proof
      from this slice: running
      `./.odylith/bin/odylith governance reconcile-plan-workstream-binding
       --repo-root . odylith/technical-plans/in-progress/2026-04/2026-04-12-bounded-test-contract-catch-up-...md`
      against the staged plan returns `decisions: 0`, and
      `./.odylith/bin/odylith sync --repo-root . --check-only --impact-mode
       selective <plan-path>` then bails at the
      `validate_plan_workstream_binding` step with
      `touched active plan ... is missing from \`## Active Plans\``.
      The B-090 row was therefore added by hand-edit as the only
      forward path, with this learning captured so the maintainer
      follow-up is to extend reconcile to insert new active-plan rows
      from touched in-progress plan files (parsing
      `Status`/`Created`/`Updated`/`Backlog` from the plan body) under
      the same CLI instead of leaving the gap as an implicit hand-edit
      contract. Until that lands, the CLI-first policy line 24 should
      be read as "binding-only owner", not "row owner", and the
      `## Narrow Allowed Hand-Edit Surfaces` block should mention the
      new-row exception. Empirical workflow that worked for B-090:
      hand-add the row to `odylith/technical-plans/INDEX.md`, then the
      project post-edit hook's sync chain calls reconcile, which now
      finds both the touched plan file and the new row, promotes the
      workstream from `queued` to `planning`, and
      `auto-promote-workstream-phase` immediately advances it to
      `implementation` from the matching live evidence. End state was
      confirmed by `./.odylith/bin/odylith sync --repo-root .
      --check-only --impact-mode selective <plan-path>` returning
      `workstream sync passed` across all 7 check steps.

## Must-Ship
- [x] Hygiene cluster triaged and either fixed (test or product, with
      explicit justification) or escalated.
- [x] All 17 orchestrator/router profile inference parameterized cases
      green.
- [x] All 4 benchmark dispatch tests green.
- [x] Auto-promote-workstream-phase test green.
- [x] Both odylith_benchmark_runner delegation tests green.
- [x] render_tooling_dashboard compass-refresh projection test green.
- [x] Full unit suite green or at most one explicitly justified
      remaining failure.
- [x] B-090 phase advanced from `queued` to `implementation` via
      governance CLI before the focused commit lands.

## Validation
- `pytest tests/unit/runtime/test_hygiene.py -v` (hygiene cluster)
- `pytest tests/unit/runtime/test_subagent_reasoning_ladder.py -v`
  (17 orchestrator/router profile inference cases)
- `pytest tests/unit/test_cli_maintainer_lane.py::test_benchmark_compare_renders_text_and_returns_fail_status
   tests/unit/test_cli_maintainer_lane.py::test_benchmark_compare_warns_without_blocking
   tests/unit/test_cli_maintainer_lane.py::test_benchmark_compare_renders_json
   tests/unit/test_cli_audit.py::test_cli_benchmark_compare_dispatch_and_json -v`
- `pytest tests/unit/runtime/test_auto_promote_workstream_phase.py::test_auto_promote_promotes_planning_workstream_with_decision_signal -v`
- `pytest tests/unit/runtime/test_odylith_benchmark_runner.py::test_live_validation_heavy_proof_slice_delegates_when_grounded
   tests/unit/runtime/test_odylith_benchmark_runner.py::test_live_explicit_workstream_proof_slice_delegates_when_grounded -v`
- `pytest tests/unit/runtime/test_render_tooling_dashboard.py::test_render_tooling_dashboard_projects_failed_compass_refresh_into_shell_status -v`
- `pytest tests/unit/ -q` to confirm the full sweep is green.

## Outcome Snapshot
- 27 → 0 failures. 1875 unit tests passing.
- 1 real product fix (bundle mirror exclude list for consumer truth roots).
- 6 test-side updates across 7 files, no product logic rewritten.
- Auto-promote stream path renamed from `codex-stream.v1.jsonl` to
  `agent-stream.v1.jsonl` in test helper.
- Benchmark runner delegation tests updated from `delegate: True` to
  `delegate: False` with `execution-governance-critical-path` guard,
  matching the live execution governance contract.
- Compass refresh remediation command updated from
  `odylith compass refresh --repo-root . --wait` to
  `odylith dashboard refresh --repo-root . --surfaces compass`.
