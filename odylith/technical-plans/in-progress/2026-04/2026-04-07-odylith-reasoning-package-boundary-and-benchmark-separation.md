Status: In progress

Created: 2026-04-07

Updated: 2026-04-08

Backlog: B-061

Goal: Separate Tribunal, Remediator, and shared reasoning-provider code from
benchmark/eval packaging without changing runtime behavior, then prove the new
boundary with regression and edge-case coverage.

Assumptions:
- The current benchmark harness may depend on shared reasoning helpers, but it
  does not need to own the reasoning implementation package.
- Internal callers and governed source references can move to the new
  `odylith.runtime.reasoning` package in one bounded refactor.
- The separation should preserve persisted artifact names and the public CLI
  contract.

Constraints:
- Do not change Tribunal decision logic or benchmark scoring semantics as part
  of the package move.
- Keep benchmark isolation truthful by stripping or preserving the right files
  after the reasoning path move.
- Keep Registry source, forensics, and traceability references aligned with the
  new source paths in the same change.

Reversibility: The package move is reversible by moving the files back, but the
intended end state for this slice is that the old eval-path modules do not
exist.

Boundary Conditions:
- Scope includes source-package layout, imports, Registry path references, and
  regression coverage.
- Scope excludes benchmark corpus redesign, Tribunal policy redesign, and any
  rename of persisted reasoning artifacts.

Related Bugs:
- [CB-045](../../casebook/bugs/2026-04-02-benchmark-live-result-recovery-drops-schema-valid-agent-message-when-last-message-file-is-missing.md)

## Learnings
- [x] Reasoning and benchmark code are now physically separated, with Tribunal,
      Remediator, and shared helpers living only under
      `src/odylith/runtime/reasoning/`.
- [x] The live package move was not fully proven until strict `sync --check-only`
      passed; Atlas catalog freshness and delivery-intelligence freshness were
      the active governed surfaces still carrying deleted eval-path references.
- [x] Maintainer validation also enforces guidance portability, so governed
      validation records must prefer portable `python3 -m pytest` forms over
      virtualenv-path pytest launchers.

## Must-Ship
- [x] Create `src/odylith/runtime/reasoning/` and move the implementation for
      `odylith_reasoning`, `tribunal_engine`, and `remediator` into it.
- [x] Delete the legacy `runtime/evaluation` copies of those reasoning module
      files.
- [x] Update internal callers to import reasoning from the new package.
- [x] Update benchmark isolation and related path-based checks to understand
      the moved reasoning files.
- [x] Update Registry/spec/forensics references to the new reasoning paths.
- [x] Add regression and edge-case tests that prove the new import paths work
      and the old eval-path modules are gone.

## Should-Ship
- [x] Add one focused package-layout test that proves the moved modules only
      resolve from `runtime/reasoning` and that sync-governed Atlas and
      delivery-intelligence inputs no longer claim the deleted eval paths.
- [x] Include a broader runtime regression sweep for delivery intelligence,
      Compass reasoning-provider use, governed-surface sync, and browser-facing
      shell surfaces.

## Defer
- [ ] Broader benchmark-corpus or ablation changes stay in their own
      workstreams.
- [ ] Deeper Tribunal internal decomposition stays out of scope for this
      boundary move.

## Success Criteria
- [x] Reasoning implementation lives under its own runtime package.
- [x] Benchmark/eval code reads reasoning through the new package boundary.
- [x] Legacy evaluation module paths for Tribunal, Remediator, and shared
      reasoning no longer exist.
- [x] Registry source and forensics no longer claim the old reasoning source
      paths as canonical.
- [x] Focused regression, edge-case, browser, and broader runtime tests all
      pass.

## Non-Goals
- [ ] Changing persisted reasoning contract filenames or CLI verbs.
- [ ] Rewriting benchmark public docs beyond the source-path alignment needed
      for this move.

## Open Questions
- [x] No B-061-scoped open question remains. Residual live benchmark transport
      flake risk stays tracked separately in `CB-045`.

## Impacted Areas
- [ ] [consumer_profile.py](/Users/freedom/code/odylith/src/odylith/runtime/common/consumer_profile.py)
- [ ] [delivery_intelligence_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/delivery_intelligence_engine.py)
- [ ] [compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py)
- [ ] [compass_standup_brief_narrator.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_standup_brief_narrator.py)
- [ ] [odylith_benchmark_isolation.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_isolation.py)
- [ ] [odylith_benchmark_live_execution.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py)
- [ ] [__init__.py](/Users/freedom/code/odylith/src/odylith/runtime/reasoning/__init__.py)
- [ ] [odylith_reasoning.py](/Users/freedom/code/odylith/src/odylith/runtime/reasoning/odylith_reasoning.py)
- [ ] [tribunal_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/reasoning/tribunal_engine.py)
- [ ] [remediator.py](/Users/freedom/code/odylith/src/odylith/runtime/reasoning/remediator.py)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/tribunal/CURRENT_SPEC.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/remediator/CURRENT_SPEC.md)
- [ ] [FORENSICS.v1.json](/Users/freedom/code/odylith/odylith/registry/source/components/tribunal/FORENSICS.v1.json)
- [ ] [FORENSICS.v1.json](/Users/freedom/code/odylith/odylith/registry/source/components/remediator/FORENSICS.v1.json)
- [ ] [diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [ ] [delivery_intelligence.v4.json](/Users/freedom/code/odylith/odylith/runtime/delivery_intelligence.v4.json)
- [ ] [test_odylith_reasoning.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_reasoning.py)
- [ ] [test_tribunal_engine.py](/Users/freedom/code/odylith/tests/unit/runtime/test_tribunal_engine.py)
- [ ] [test_remediator.py](/Users/freedom/code/odylith/tests/unit/runtime/test_remediator.py)
- [ ] [test_odylith_benchmark_live_execution.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_live_execution.py)
- [ ] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)
- [ ] [test_reasoning_package_layout.py](/Users/freedom/code/odylith/tests/unit/runtime/test_reasoning_package_layout.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_reasoning.py tests/unit/runtime/test_tribunal_engine.py tests/unit/runtime/test_remediator.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_live_execution.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_isolation.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_reasoning_package_layout.py tests/unit/runtime/test_sync_component_spec_requirements.py tests/unit/test_cli_audit.py tests/unit/test_cli_maintainer_lane.py`
      (`85 passed`)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
      (passed after Atlas and delivery-intelligence freshness refresh)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
      (`71 passed, 1 skipped`)
- [x] `make dev-validate`
      (`1449 passed, 1 skipped`)
- [x] `PYTHONPATH=src python3 -B -m odylith.cli benchmark --repo-root . --profile quick --family architecture --shard-count 2 --shard-index 1 --limit 1 --no-write-report --json`
      (rerun report `44c05c52c2551121`, `provisional_pass`; an earlier same-slice run hit the separately tracked `CB-045` transport flake before passing on rerun)
- [x] `git diff --check`
