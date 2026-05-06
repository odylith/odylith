- Bug ID: CB-173

- Status: Open

- Created: 2026-05-06

- Severity: P1

- Reproducibility: High

- Type: OperatorUX

- Description: Greenfield apply drip-fails loose host proposals and leaves partial governance writes

- Impact: A fresh greenfield proposal can take multiple manual repair loops, leave duplicate Radar ideas, stale Registry and Atlas source, stale release assignment events, and force the operator into hand cleanup before retry.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Consumer-lane installed repo with no app source, observed from a recipe-sharing app greenfield proposal flow on 2026-05-06.

- Detected By: Operator transcript showing repeated greenfield apply Tribunal failures, partial writes, cleanup prompts, blocked recursive deletion, duplicate active ideas, stale Atlas catalog entries, unknown release workstream events, and a late Mermaid render failure.

- Failure Signature: greenfield apply rejected mode/schema fields, release plan gates, component proof fields, diagram workstream refs, invalid qualification greenfield, duplicate active ideas, slug already exists, unknown workstream release events, and Mermaid sequence render syntax after source writes.

- Trigger Path: odylith show on an empty repo, host-authored recipe-sharing proposal, odylith greenfield apply --confirm --release 0.0.1, retry after each failure.

- Ownership: Domain Intelligence greenfield proposal normalization, deterministic apply transaction boundary, Proposal Tribunal compatibility, Atlas diagram source normalization, and greenfield operator guidance.

- Timeline: 2026-05-06: operator reproduced on a recipe-sharing app prompt; apply failed across schema, Tribunal, Atlas, release-event, and Mermaid render stages and required manual source cleanup.

- Blast Radius: All empty or thin consumer repos using greenfield propose/apply through Codex or Claude host reasoning.

- SLO/SLA Impact: Breaks low-latency greenfield onboarding and can turn a first-run proposal apply into a multi-minute manual cleanup path.

- Data Risk: Governance source truth can be left split-brain with duplicate workstreams, stale Registry entries, stale Atlas catalog/source, and release events referencing removed workstreams; no application data is affected.

- Security/Compliance: No direct credential or regulated-data exposure observed, but security/compliance posture for consumer app proposals was under-specified by the first-run contract before this fix.

- Invariant Violated: Confirmed greenfield apply must validate or normalize common host-authored proposal shapes before writes, and any failed apply must leave governed source truth retry-safe.

- Workaround: Manually delete generated partial Radar ideas, Registry source, Atlas source/catalog entries, release event files, reset Radar INDEX rows, then retry apply.

- Root Cause: Apply expected an exact internal schema from host-authored JSON, accepted only backlog-title diagram refs, wrote source truth before all late failures were impossible, reused generic diagram slugs, and let Mermaid sequence punctuation reach render-time validation.

- Solution: Normalize common host-authored proposal shapes before validation; expose a canonical host-authored JSON template in `greenfield propose`; accept workstream IDs as diagram traceability aliases; namespace partially scoped generic diagram slugs before Atlas scaffold; normalize sequence message punctuation; wrap greenfield source-truth and generated dashboard writes in a rollback transaction; deepen proposal guidance for security, privacy, compliance, abuse, accessibility, retention, and operational risks.

- Rollback/Forward Fix: Forward fix in domain_intelligence greenfield apply, Proposal Tribunal, proposal normalization, rollback guard, greenfield skill guidance, and regression tests.

- Verification: PYTHONPATH=src python3.13 -m pytest -q tests/unit/test_cli.py::test_greenfield_propose_help_forwards_backend_flags tests/unit/test_cli.py::test_greenfield_apply_help_forwards_backend_flags tests/unit/test_cli.py::test_greenfield_propose_command_is_provider_free tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_surface_shell_contracts.py tests/unit/runtime/test_dashboard_ui_primitives.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_release_planning.py tests/unit/runtime/test_greenfield_host_routing.py tests/integration/runtime/test_surface_browser_smoke.py::test_compass_and_radar_target_release_cards_show_labeled_release_version; PYTHONPATH=src python3.13 -m compileall -q src/odylith/runtime/domain_intelligence/greenfield_proposals.py src/odylith/runtime/domain_intelligence/proposal_contract.py src/odylith/runtime/domain_intelligence/proposal_rendering.py src/odylith/runtime/domain_intelligence/proposal_normalization.py src/odylith/runtime/domain_intelligence/greenfield_transaction.py; git diff --check on touched files; greenfield propose brief includes canonical apply JSON shape, security/compliance, and parser-safe sequence guidance.

- Prevention: Keep a regression fixture shaped like the operator transcript, including mode greenfield, release_plan list, component proof_expectations, diagram refs by WS ids, generic slugs, qualification greenfield, and sequence labels with semicolons.

- Agent Guardrails: Do not ask the operator to hand-clean partial governance writes after an apply failure; the product path must either fail before writes or rollback source truth automatically.

- Preflight Checks: Before greenfield apply writes, normalize proposal shape and run deterministic validation plus Tribunal; after acceptance, one batched visibility refresh only.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_normalizes_common_host_authored_recipe_shape, tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_namespaces_partial_project_diagram_slugs_before_scaffold, tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_rolls_back_partial_writes_when_late_step_fails, and tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_rolls_back_generated_surfaces_when_refresh_fails.

- Monitoring Updates: Watch greenfield support transcripts for duplicate active ideas, slug already exists, unknown workstream release events, and late Mermaid render failures after apply.

- Version/Build: v0.1.15 maintainer branch 2026/freedom/v0.1.15

- Config/Flags: Default greenfield release selector 0.0.1; no feature flag.

- Customer Comms: Release notes should state that greenfield apply now normalizes common host proposal shapes and rolls back failed source-truth writes.

- Related Incidents/Bugs: Related: 2026-05-03-greenfield-consumer-intent-dead-ended-on-missing-source; 2026-05-04-greenfield-apply-target-release-can-stay-invisible-in-radar-and-compass; 2026-05-03-greenfield-atlas-drafts-reuse-generic-star-topology.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_proposals.py
- src/odylith/runtime/domain_intelligence/proposal_normalization.py
- src/odylith/runtime/domain_intelligence/greenfield_transaction.py
- src/odylith/runtime/domain_intelligence/proposal_tribunal.py
- tests/unit/runtime/test_greenfield_proposals.py
