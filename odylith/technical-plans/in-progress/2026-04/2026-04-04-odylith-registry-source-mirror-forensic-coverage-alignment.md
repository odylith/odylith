Status: In progress

Created: 2026-04-04

Updated: 2026-04-04

Backlog: B-045

Goal: Make Registry forensic coverage treat source-owned mirrored component
paths as live evidence for the owning component without widening benchmark or
generic generated-file behavior.

Assumptions:
- The current gap is in component workspace-activity mapping, not in the
  renderer labels or sidecar write path.
- Canonical source paths should remain the primary ownership contract.
- The Odylith bundle layout is stable enough to support a narrow mirror-aware
  mapping rule.

Constraints:
- Do not broaden benchmark snapshot planning or dirty-worktree semantics.
- Do not make generic generated assets count as component forensic evidence.
- Keep explicit Compass events as the preferred source of durable component
  narrative.
- Avoid cross-component false positives when one mirrored path changes.

Reversibility: The mapper and tests are forward-fix changes but can be locally
reverted if mirror-aware mapping proves too permissive.

Boundary Conditions:
- Scope includes Registry forensic workspace-activity mapping, focused tests,
  forensic sidecar refresh, and touched governance records.
- Scope excludes benchmark scenario contracts, surface redesign, and Compass
  logging semantics.

Related Bugs:
- [2026-04-04-registry-live-forensics-miss-source-owned-bundle-mirror-component-activity.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-04-registry-live-forensics-miss-source-owned-bundle-mirror-component-activity.md)

## Must-Ship
- [ ] Mirror-aware component evidence mapping lands in Registry workspace
      activity handling.
- [ ] Focused regression coverage proves the affected component becomes live on
      source-owned mirror edits alone.
- [ ] Unrelated generated or mirrored paths still stay excluded.
- [ ] Registry forensic artifacts refresh cleanly after the fix.

## Should-Ship
- [ ] Keep the rule narrow enough that future explicit manifest metadata can
      replace it cleanly.
- [ ] Document the benchmark-safe constraint in the plan and validation path.

## Defer
- [ ] Manifest-level explicit mirror metadata.
- [ ] Broader generated-asset ownership normalization across all surfaces.

## Success Criteria
- [ ] `tribunal` and `remediator` no longer stay baseline-only when their
      source-owned mirrored runtime docs are the only active changes.
- [ ] Registry still excludes unrelated generated churn from workspace
      activity evidence.
- [ ] Focused benchmark-facing validation remains green.

## Impacted Areas
- [ ] [component_registry_intelligence.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/component_registry_intelligence.py)
- [ ] [render_registry_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_registry_dashboard.py)
- [ ] [test_render_registry_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_registry_dashboard.py)
- [ ] [test_sync_component_spec_requirements.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_component_spec_requirements.py)
- [ ] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)
- [ ] [test_odylith_benchmark_prompt_payloads.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_prompt_payloads.py)
- [ ] [2026-04-04-odylith-registry-source-mirror-forensic-coverage-alignment.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-04-odylith-registry-source-mirror-forensic-coverage-alignment.md)
- [ ] [2026-04-04-registry-live-forensics-miss-source-owned-bundle-mirror-component-activity.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-04-registry-live-forensics-miss-source-owned-bundle-mirror-component-activity.md)

## Risks & Mitigations
- [ ] Risk: mirror-aware matching maps one bundle file to the wrong component.
  - [ ] Mitigation: keep mapping deterministic and anchored to canonical
        source-owned path prefixes only.
- [ ] Risk: benchmark behavior changes by accident through shared dirty-path
      helpers.
  - [ ] Mitigation: keep the change inside Registry component evidence mapping
        and run focused benchmark tests before closeout.

## Validation/Test Plan
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_sync_component_spec_requirements.py`
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_prompt_payloads.py`
- [ ] `PYTHONPATH=src python -m odylith.runtime.governance.sync_component_spec_requirements --repo-root . --component tribunal --component remediator --check-only`
- [ ] `git diff --check`

## Rollout/Communication
- [ ] Refresh Registry-side forensic truth after the mapper change lands.
- [ ] Keep the explanation grounded in evidence accuracy, not broader mirror
      policy changes.

## Current Outcome
- [x] `B-045` opened to isolate Registry source-mirror forensic coverage.
- [ ] Mapper change, regressions, and validation are in progress.
