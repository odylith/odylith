- Bug ID: CB-341

- Status: Open

- Created: 2026-08-18

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The graph-authority severance deleted proposal_tribunal.py, but the product capability inventory still named it as a Tribunal anchor. Engine integrity therefore reports one stale-anchor warning on an otherwise fully wired 22-area engine spine, creating operational risk that maintainers follow a deleted authority path.

- Impact: Canonical validation fails and the operator integrity report cannot truthfully claim a clean engine inventory after the Greenfield authority replacement. The delivery risk is release delay and incorrect architecture guidance.

- Components Affected: odylith

- Environment(s): Detached source-local maintainer worktree on 2026-08-18 during canonical dev-validation shard 9.

- Detected By: test_engine_integrity_text_report_is_operator_readable in the fail-fast 4,399-test corpus.

- Failure Signature: WARNING Tribunal: Tribunal has stale anchor references: src/odylith/runtime/domain_intelligence/proposal_tribunal.py.

- Trigger Path: PYTHONPATH=src .venv/bin/python -m pytest -q -x tests/unit/runtime/test_engine_integrity.py::test_engine_integrity_text_report_is_operator_readable

- Ownership: Product capability inventory and engine-integrity source-anchor contract.

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: Engine integrity reports, capability-map trust, and release validation.

- SLO/SLA Impact: Blocks release convergence; no installed runtime outage.

- Data Risk: No application data is mutated, but stale architecture truth can route future changes to a deleted module and fragment semantic ownership.

- Security/Compliance: No direct security exposure, but inaccurate engine inventory weakens auditability of the pre-write adjudication boundary.

- Invariant Violated: Every advertised engine anchor must exist and describe the current authority path; deleted mechanisms must not survive in product inventory.

- Root Cause: The Greenfield graph-only severance removed the proposal Tribunal implementation without updating the Tribunal capability inventory anchor and activation narrative.

- Solution: Replace the deleted anchor with the current semantic materiality challenge contract and describe the split accurately: governed bug writes use artifact Tribunal, while Greenfield requires an independent prompt-only materiality challenge before deterministic publication.

- Rollback/Forward Fix: Forward fix capability truth only; do not restore the deleted proposal Tribunal.

- Verification: Run the exact engine-integrity test file and canonical shard 9.

- Prevention: Authority-deletion waves must include capability-inventory and engine-integrity structural scans for deleted paths.

- Agent Guardrails: Never silence stale-anchor warnings or weaken engine integrity. Update product truth to the surviving owner and prove the old path is absent.

- Preflight Checks: Confirm the replacement materiality contract exists and the deleted proposal Tribunal has no surviving runtime file.

- Regression Tests Added: tests/unit/runtime/test_engine_integrity.py

- Version/Build: Greenfield semantic graph source-local release candidate based on bf982b0e.

- Related Incidents/Bugs: CB-340

- Code References: - src/odylith/runtime/analysis_engine/capability_inventory.py
- src/odylith/runtime/domain_intelligence/greenfield_semantic_materiality_contract.py
- tests/unit/runtime/test_engine_integrity.py
