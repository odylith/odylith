- Bug ID: CB-038

- Status: Closed

- Created: 2026-04-02

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: In the consumer lane, `odylith dashboard refresh --repo-root .`
  refreshed only `tooling_shell` and `radar` by default but did not say
  plainly which surfaces were skipped, so Compass and Atlas staleness could
  look like a broken refresh. When the operator did opt into
  `--surfaces atlas --atlas-sync`, Odylith could spend a long bulk-render pass
  before surfacing a Mermaid parse failure, and the final error did not point
  cleanly at the blocking `.mmd` path and line.

- Impact: Operators could mistrust the dashboard refresh path, miss that Atlas
  had been intentionally excluded, and lose time digging through Atlas refresh
  failures that should have been reported immediately and precisely.

- Components Affected: `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`, dashboard
  refresh operator contract, Atlas refresh diagnostics.

- Environment(s): Consumer lane, `odylith dashboard refresh --repo-root .`,
  `odylith atlas auto-update --repo-root . --all-stale`, release hardening
  validation.

- Root Cause: The default dashboard-refresh surface set excluded Compass and
  Atlas, but the command output did not enumerate the included versus excluded
  surfaces or print the Atlas follow-up path when Atlas was stale. Separately,
  Atlas auto-update validated Mermaid source only inside the render flow, so
  syntax errors surfaced late and the final summary collapsed the failure into
  a generic error string.

- Solution: Make the default dashboard refresh include Compass, print the
  included and excluded surfaces plus the exact Atlas next command, add a fast
  Mermaid syntax preflight before the Atlas render batch, and surface parse
  failures with diagram id, source path, line, and line context.

- Verification: `pytest -q tests/unit/test_cli.py
  tests/unit/runtime/test_sync_cli_compat.py
  tests/unit/runtime/test_auto_update_mermaid_diagrams.py` passed with `80
  passed`; `pytest -q
  tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_cli_install_adopt_latest_renders_a_browser_valid_incremental_upgrade_note
  tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_cli_upgrade_renders_a_browser_valid_incremental_upgrade_note`
  passed with `2 passed`.

- Prevention: Any narrow refresh command must print its exact surface scope in
  operator-facing output, and Atlas source validation must happen before
  expensive render work starts.

- Detected By: Consumer-lane feedback during release validation on 2026-04-02
  after a repo-local Mermaid syntax defect in a downstream Atlas source.

- Failure Signature: `odylith dashboard refresh --repo-root .` appeared to
  succeed while Compass or Atlas remained stale, or `odylith atlas auto-update`
  failed only after a long render attempt with no immediate `diagram_id`
  plus `.mmd:line` diagnosis.

- Trigger Path: `odylith dashboard refresh --repo-root .`,
  `odylith dashboard refresh --repo-root . --surfaces atlas --atlas-sync`,
  `odylith atlas auto-update --repo-root . --all-stale`

- Ownership: Dashboard refresh contract, Atlas refresh diagnostics, consumer
  release ergonomics.

- Timeline: Consumer-lane feedback isolated the downstream broken Mermaid as
  repo-local truth, then pointed back at the Odylith-product gap: surface
  selection stayed implicit and Atlas diagnostics arrived too late. The
  release-hardening slice was extended so refresh scope is explicit and Atlas
  syntax failures stop before bulk render.

- Blast Radius: Consumer upgrade follow-up, shell trust, Atlas repair loops,
  and release validation time.

- SLO/SLA Impact: Refresh and repair remained recoverable but burned operator
  time and weakened trust in the narrow refresh path.

- Data Risk: Low direct data risk; moderate governance-truth workflow risk
  because Atlas review metadata could look stale or confusing longer than
  necessary.

- Security/Compliance: None beyond normal local-truth integrity expectations.

- Invariant Violated: Narrow refresh must say what it refreshed, and Atlas
  syntax errors must fail fast with precise source diagnosis before render.

- Workaround: Manually rerun Atlas refresh with explicit `--surfaces atlas
  --atlas-sync`, then inspect downstream Mermaid source by hand.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not blame Odylith for repo-local Mermaid syntax defects,
  but do treat missing surface-selection output or late Atlas parse diagnosis
  as product bugs worth fixing in the release lane.

- Preflight Checks: Inspect default dashboard refresh surfaces, dashboard
  execution-plan notes, Atlas auto-update error summaries, and Mermaid worker
  validation coverage before changing shell refresh ergonomics again.

- Regression Tests Added:
  `test_dashboard_refresh_plan_reports_included_excluded_surfaces_and_atlas_follow_up`,
  `test_mermaid_worker_request_raises_validation_error_for_structured_response`,
  `test_atlas_auto_update_fails_fast_on_mermaid_validation_error`

- Monitoring Updates: Dashboard refresh now prints included and excluded
  surfaces plus the Atlas next command, and Atlas auto-update prints the
  blocking `.mmd:line` before any render batch work completes.

- Residual Risk: Atlas parse preflight still depends on the Mermaid parser used
  by the pinned CLI toolchain, so parser-version upgrades need the same
  fail-fast coverage to stay trustworthy.

- Related Incidents/Bugs: None in Odylith Casebook; downstream consumer-lane
  feedback provided the motivating repro.

- Version/Build: `v0.1.7` release hardening on 2026-04-02.

- Config/Flags: `odylith dashboard refresh --repo-root .`,
  `--surfaces atlas --atlas-sync`, `odylith atlas auto-update --repo-root .
  --all-stale`

- Customer Comms: Public install and surface-ops guidance should say the
  default refresh surfaces explicitly and call out Atlas as an opt-in source
  refresh with fast syntax diagnostics.

- Code References: `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`,
  `tests/unit/runtime/test_sync_cli_compat.py`,
  `tests/unit/runtime/test_auto_update_mermaid_diagrams.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`,
  `odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md`,
  `odylith/registry/source/components/dashboard/CURRENT_SPEC.md`,
  `odylith/registry/source/components/atlas/CURRENT_SPEC.md`

- Fix Commit/PR: Pending.
