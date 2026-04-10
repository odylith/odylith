- Bug ID: CB-090

- Status: Open

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Odylith's governance surfaces were still deriving urgency and
  visibility locally. A scope could look important in Compass, quiet in Radar,
  promoted in Atlas, and still float near the top of Registry even when the
  underlying evidence was only governance-file churn, generated noise, or a
  broad fanout transaction. The same split also wasted compute budget because
  nothing centrally decided which scopes were allowed to buy fresh narration or
  reasoning work.

- Impact: Low-signal work can steal operator attention, expensive compute, and
  default-surface prominence away from real implementation or blocker scopes.

- Components Affected: `src/odylith/runtime/governance/delivery_intelligence_engine.py`,
  `src/odylith/runtime/governance/delivery/scope_signal_ladder.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/render_backlog_ui_payload_runtime.py`,
  `src/odylith/runtime/surfaces/render_registry_dashboard.py`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`,
  related specs and governance-surface guidance.

- Environment(s): Odylith product-repo maintainer mode, rendered Compass,
  Radar, Registry, Atlas, and any downstream consumer reading delivery
  intelligence without a shared scope-escalation contract.

- Root Cause: Default visibility, promotion, and budget gating were implicit
  local policy spread across multiple renderers and runtime builders. The
  product had no one additive `scope_signal` contract for low-signal noise,
  verified local movement, active execution, actionable warning posture, and
  blocker-frontier escalation.

- Solution: Introduce a deterministic shared Scope Signal Ladder under
  Delivery Intelligence, persist the additive `scope_signal` payload on
  delivery snapshots, and make Compass, Radar, Registry, Atlas, and shared
  budget decisions read that one contract instead of rebuilding urgency
  locally.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_scope_signal_ladder.py tests/unit/runtime/test_delivery_intelligence_engine.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_refresh_runtime.py tests/unit/runtime/test_compass_standup_brief_batch.py tests/unit/runtime/test_compass_window_update_index.py tests/unit/runtime/test_render_backlog_ui_payload_runtime.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_proof_state_runtime.py tests/unit/runtime/test_release_planning.py tests/unit/runtime/test_release_truth_runtime.py tests/unit/runtime/test_tooling_dashboard_surface_status.py tests/unit/runtime/test_workstream_progress.py`
  - `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
  - `PYTHONPATH=src python3 -m odylith.cli atlas render --repo-root .`
  - `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --runtime-mode standalone --proceed-with-overlap`
  - `git diff --check`

- Prevention: Keep scope visibility, promotion, and expensive compute budgets
  under one shared ladder contract with explicit rung reasons, caps, parent
  rollups, and provider-neutral budget classes.

- Detected By: Repeated Compass scope-selector regressions and cross-surface
  operator feedback showing that low-signal governance churn kept reappearing
  as default-visible "activity."

- Failure Signature: Quiet scopes show up as locally active in one surface,
  unrelated wide fanout or governance-only rows dominate default focus, and the
  runtime spends fresh narration or reasoning budget on scopes that did not
  earn it.

- Trigger Path: 1. Produce governance-only local churn, generated-only churn,
  or broad fanout transactions. 2. Open Compass, Radar, Registry, or Atlas in
  their default operational views. 3. Compare which scopes are promoted first.

- Ownership: Delivery Intelligence as the single owner of scope escalation,
  plus Compass/Radar/Registry/Atlas consumers.

- Invariant Violated: One repo state must not produce four different answers to
  "which scopes deserve default operator attention and fresh expensive compute
  right now?"

- Workaround: Treat local detail truth as more trustworthy than the promoted
  default views and avoid spending fresh provider work on scoped refreshes.
  That is not an acceptable product contract.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not infer urgency from local heuristics once the shared
  `scope_signal` contract exists. Low-signal noise belongs in raw evidence or
  explicit deep links, not in default promotion or provider budget.

- Regression Tests Added:
  - `tests/unit/runtime/test_scope_signal_ladder.py`
  - `tests/unit/runtime/test_delivery_intelligence_engine.py`
  - `tests/unit/runtime/test_compass_dashboard_runtime.py`
  - `tests/unit/runtime/test_render_backlog_ui_payload_runtime.py`
  - `tests/unit/runtime/test_render_backlog_ui.py`
  - `tests/unit/runtime/test_render_registry_dashboard.py`
  - `tests/unit/runtime/test_render_mermaid_catalog.py`
  - `tests/integration/runtime/test_surface_browser_deep.py`
  - `tests/integration/runtime/test_surface_browser_smoke.py`

- Related Incidents/Bugs:
  [2026-04-09-compass-scoped-selector-can-advertise-unverified-window-activity-and-leak-global-audit-cards.md](2026-04-09-compass-scoped-selector-can-advertise-unverified-window-activity-and-leak-global-audit-cards.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Follow-Up Notes:
  - The shared ladder rollout is complete and browser-green, but Compass
    refresh latency is still above the founder budget target. The ladder did
    not regress the current envelope; measured source-local shell-safe runs
    after rollout were `real 2.03` on the first run and `real 1.25` on the
    immediate rerun.
