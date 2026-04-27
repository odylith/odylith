- Bug ID: CB-087

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass `Release Targets`, Compass workstream rows, Radar
  execution-wave summaries, and Compass narrative helpers could all treat a
  raw `plan.progress_ratio = 0.0` as if it were a truthful `0% execution
  progress` claim. That was wrong for active implementation lanes whose
  execution checklist existed but had no checked items yet, and it was made
  worse by `plan_progress.py` counting non-execution checklist sections such as
  `Learnings`, `Defer`, `Non-Goals`, `Impacted Areas`, `Traceability`, and
  `Open Questions` into the visible percent. On 2026-04-09 this showed up
  directly on `B-068`, where the benchmark family was materially implemented
  but `Release Targets` still showed `0% progress`.

- Impact: Operators could see an active workstream and conclude that no real
  work had been completed when the actual problem was stale checklist capture
  or diluted progress math. That damages trust in release targeting, Radar
  workstream posture, and Compass standup narration.

- Components Affected: `src/odylith/runtime/governance/plan_progress.py`,
  `src/odylith/runtime/governance/workstream_progress.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/render_backlog_ui_payload_runtime.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-waves.v1.js`,
  `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`,
  `src/odylith/runtime/surfaces/compass_outcome_digest_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_runtime_reuse.py`,
  `src/odylith/runtime/surfaces/compass_standup_fact_packets.py`,
  Compass and Radar component specs, and `B-068` plan truth.

- Environment(s): Product-repo maintainer mode and any bundled or rendered
  Compass/Radar surface consuming workstream plan progress.

- Root Cause: Odylith had only one plan-progress number and treated it as both
  raw checklist math and a user-facing execution-progress claim. The raw math
  itself was too broad because it counted non-execution sections, and the UI
  layer had no shared notion of `implementation is active but checklist
  progress is not yet captured`.

- Solution: Count only execution-relevant checklist sections for visible plan
  progress, add a shared workstream-progress classifier that distinguishes
  tracked progress from untracked implementation, surface checklist-only labels
  instead of `0%` when implementation has started but no execution tasks are
  checked, update Compass/Radar narrative layers to stop describing those
  lanes as planning-only, and include rendered progress semantics in Compass
  brief-reuse fingerprints so stale cached narration cannot survive a progress
  contract change.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_context_engine.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_context_engine_split_hardening.py tests/unit/runtime/test_context_engine_release_resolution.py tests/unit/runtime/test_context_engine_topology_contract.py tests/unit/runtime/test_context_engine_proof_packet_runtime.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_plan_progress.py tests/unit/runtime/test_workstream_progress.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_render_compass_dashboard.py` passed (`267 passed`). `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_deep.py::test_compass_reconciles_release_targets_from_live_traceability_when_runtime_snapshot_is_stale tests/integration/runtime/test_surface_browser_deep.py::test_compass_release_targets_show_checklist_label_instead_of_fake_zero_progress tests/integration/runtime/test_surface_browser_deep.py::test_compass_release_targets_show_tracked_execution_percent_for_partial_progress` passed. `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone` passed. `git diff --check` passed. Post-refresh audit of `odylith/compass/runtime/current.v1.json` showed `13` active implementation workstreams and `0` visible `0% progress` labels among them.

- Prevention: Raw checklist extraction and visible progress claims must stay
  distinct. If a workstream is in `implementation` and execution checklist
  progress is still zero, the surface may show checklist counts or `unknown`,
  but it must not narrate that state as `0% execution progress` without an
  explicit not-started status.

- Detected By: Maintainer review of `B-068` in `Release Targets` on
  2026-04-09.

- Failure Signature: `B-068` appears in Compass `Release Targets` as
  `Implementation` with `0% progress` even though the benchmark family, runner,
  docs, and regression suites are already landed. Global Compass posture can
  also say implementation lanes are still in planning setup because no
  checklist items are checked.

- Trigger Path: 1. Keep a workstream in `implementation`. 2. Leave its plan
  checklist untouched or diluted by non-execution sections. 3. Open Compass or
  Radar release/execution-wave views.

- Ownership: Radar plan-progress truth, shared workstream-progress semantics,
  Compass release/workstream rendering, and Compass narrative posture.

- Timeline: This surfaced during direct review of the active `v0.1.11`
  release target after the `context_engine_grounding` benchmark slice had
  already landed.

- Blast Radius: Any active workstream whose plan has many auxiliary checklist
  sections or whose execution work is underway before maintainers check the
  execution boxes.

- SLO/SLA Impact: No outage, but strong operator-trust damage in release and
  execution posture readouts.

- Data Risk: Low source-of-truth corruption risk; high posture-readout trust
  risk.

- Security/Compliance: None directly.

- Invariant Violated: Compass and Radar must not equate raw unchecked
  execution checklist state with `0%` real workstream progress once a lane is
  already in implementation.

- Workaround: Read the bound plan directly and interpret checklist counts
  manually. That is not acceptable as the product default.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: When a workstream is already in implementation, do not
  narrate `0% progress` unless the system is explicitly showing a not-started
  execution checklist for a planning or queued lane.

- Preflight Checks: Inspect `odylith/technical-plans/.../B-068` checklist
  posture, `src/odylith/runtime/governance/plan_progress.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  and `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`.

- Regression Tests Added: `tests/unit/runtime/test_plan_progress.py`,
  `tests/unit/runtime/test_workstream_progress.py`,
  `tests/unit/runtime/test_compass_dashboard_runtime.py`,
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/unit/runtime/test_render_backlog_ui.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`.

- Monitoring Updates: Watch for any `implementation` workstream that renders
  `0% progress` instead of a checklist-only or unknown state, and for any
  plan-progress extractor that reintroduces non-execution sections into the
  visible ratio. Release-target audits should also confirm tracked partial
  execution still surfaces as real percent completion rather than collapsing
  to checklist labels or raw zero.

- Residual Risk: The remaining risk is governance lag: if a plan never checks
  execution boxes, the product can now say `Checklist 0/N`, but it still
  depends on maintainers to record progress honestly.

- Related Incidents/Bugs:
  [2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md](2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Visible in default Compass and Radar readouts; no special flag
  required.

- Customer Comms: Tell operators that Compass and Radar now distinguish raw
  checklist capture from real visible progress, so implementation lanes with
  zero checked execution tasks will show checklist counts or unknown state
  instead of a misleading `0%`.

- Code References: `src/odylith/runtime/governance/plan_progress.py`,
  `src/odylith/runtime/governance/workstream_progress.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/render_backlog_ui_payload_runtime.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/registry/source/components/radar/CURRENT_SPEC.md`

- Fix Commit/PR: Pending.
