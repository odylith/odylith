- Bug ID: CB-065

- Status: Closed

- Created: 2026-04-07

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: `odylith sync` already supports selective versus full impact,
  dry-run preview, verbose overlap output, runtime-mode selection, and other
  real execution controls, but the top-level `odylith sync --help` surface does
  not expose them. During long-running consumer syncs, action-backed phases can
  also run quietly for tens of seconds with no heartbeat. Large dirty-overlap
  runs proceed without an explicit acknowledgement gate, legacy normalization is
  summarized too vaguely, and high warning counts pass without a structured
  artifact pointer.

- Impact: Operators can watch a healthy sync and still come away unsure which
  controls exist, whether the process is alive, how risky a large dirty-overlap
  mutation is, and where to inspect the full warning payload behind a "passed"
  contract. That weakens trust in one of Odylith’s core maintainer and consumer
  lifecycle paths even when the engine behaves correctly.

- Components Affected: `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/governance/validate_component_registry_contract.py`,
  sync CLI help and forwarding, sync execution-plan UX, operator warning
  summaries, overlap guardrails, and legacy-normalization reporting.

- Environment(s): Consumer and maintainer repos running `odylith sync`,
  especially large dirty worktrees with selective impact and long action-backed
  render or validation phases.

- Root Cause: The public CLI wrapper still hides the runtime sync parser shape,
  execution heartbeats only exist for subprocess-backed commands, overlap
  summaries remain advisory-only even at high counts, and warning-heavy passes
  do not consistently point operators at a durable structured report.

- Solution: Surface the real sync controls in `odylith sync --help`, add
  step-level heartbeats for long action-backed phases, require an explicit
  proceed flag past a dirty-overlap threshold, summarize legacy normalization as
  a first-class phase with counts, and print a durable warning-report pointer
  when sync passes with high warning volume.

- Verification: Fixed on 2026-04-08. `PYTHONPATH=src python3 -m pytest -q
  tests/unit/install/test_release_assets.py tests/unit/install/test_release_bootstrap.py
  tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py
  tests/unit/runtime/test_backfill_workstream_traceability.py
  tests/unit/runtime/test_delivery_intelligence_engine.py
  tests/unit/runtime/test_validate_component_registry_contract.py
  tests/integration/install/test_manager.py::test_install_bundle_align_pin_advances_existing_repo_pin_to_active_runtime
  tests/integration/install/test_manager.py::test_upgrade_prunes_runtime_and_release_cache_retention
  tests/integration/install/test_manager.py::test_upgrade_warns_and_continues_when_retention_prune_stays_permission_denied`
  passed with `176 passed in 1.75s`, covering sync help exposure, overlap
  gating, heartbeat output, normalization summaries, and warning-report
  pointers in the successful validator path.

- Prevention: Operator-facing lifecycle commands should never hide supported
  safety controls or leave long-running steps silent enough to feel hung.

- Detected By: Real downstream `odylith sync --repo-root .` feedback on
  2026-04-07 from a consumer repo.

- Failure Signature: `odylith sync --help` only showing `--repo-root`,
  successful syncs sitting quiet during long action phases, and large warning
  or overlap volumes without strong next-step guidance.

- Trigger Path: Top-level `odylith sync` CLI entrypoint, sync execution-plan
  printer, action-step execution path, and registry-validator warning summary.

- Ownership: Sync operator contract and governance sync UX.

- Timeline: Selective impact planning and compact dirty-overlap summaries
  already improved sync clarity, but the public help surface and long-running
  execution path still lag behind the runtime’s actual capabilities.

- Blast Radius: Maintainer release proof, consumer repo sync confidence, and
  any operator trying to distinguish healthy long-running work from a stuck or
  unsafe mutation.

- SLO/SLA Impact: Medium operator-confidence impact on a core lifecycle path.

- Data Risk: Low.

- Security/Compliance: Stronger overlap acknowledgement improves change-safety
  posture without weakening validation.

- Invariant Violated: A passing sync should make supported controls, current
  progress, warning evidence, and dirty-worktree risk legible to the operator.

- Workaround: Read runtime source or logs to infer supported flags, rerun with
  manual process inspection, and rely on dry-run plus human judgment for large
  overlap sets.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Preserve the selective impact model and current dry-run
  semantics; improve operator clarity without broadening default mutation scope.

- Preflight Checks: Inspect top-level sync argument forwarding, action-step
  execution, overlap summaries, and registry warning reporting before changing
  the public help surface.

- Regression Tests Added:
  `tests/unit/test_cli.py`,
  `tests/unit/runtime/test_sync_cli_compat.py`,
  `tests/unit/runtime/test_validate_component_registry_contract.py`

- Monitoring Updates: Watch downstream sync feedback for missing-help,
  silent-progress, and overlap-guard complaints after the improved operator
  surface ships.

- Residual Risk: Some low-signal repo or dependency warnings may still need
  separate bucketing after the operator-surface hardening lands.

- Related Incidents/Bugs:
  [CB-059](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-sync-failure-summary-repeats-verbose-output-and-stale-next-action.md),
  [CB-060](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-lifecycle-plans-print-full-dirty-overlap-by-default.md)

- Version/Build: Odylith `0.1.9` observed on 2026-04-07 during downstream
  consumer sync on macOS Apple Silicon.

- Config/Flags: Default `odylith sync --repo-root .` path and
  `odylith sync --help`.

- Customer Comms: Sync itself planned and completed well, but the operator
  surface still hid real controls and spent too long looking uncertain. The fix
  makes the same healthy engine feel deliberate and auditable.

- Code References: `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/governance/validate_component_registry_contract.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: `2026/freedom/v0.1.10` sync-operator hardening series.
