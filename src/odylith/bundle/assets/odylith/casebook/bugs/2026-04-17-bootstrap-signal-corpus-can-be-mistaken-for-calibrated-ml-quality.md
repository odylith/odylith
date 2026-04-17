- Bug ID: CB-123

- Status: Open

- Created: 2026-04-17

- Severity: P1

- Reproducibility: Consistent

- Type: product-trust

- Description: Bootstrap signal corpus can be mistaken for calibrated ML quality

- Impact: If bootstrap or synthetic selector cases are reported as calibrated ML quality, Odylith can overclaim precision and spend brand trust on an unproven signal selector.

- Components Affected: governance-intervention-engine

- Environment(s): v0.1.11 maintainer implementation of the visible intervention value engine under B-096.

- Detected By: Maintainer review during the chat-visible intervention hardening plan.

- Failure Signature: Seed cases and hand-set weights can look like calibrated ML unless corpus origin, density gates, and runtime posture explicitly say bootstrap deterministic_utility_v1.

- Trigger Path: Building intervention signal selection from a small seed corpus or synthetic boundary cases without publishable real transcript adjudication density.

- Ownership: governance-intervention-engine value engine, intervention-value adjudication corpus, and benchmark reporting.

- Timeline: 2026-04-17: user rejected the arithmetic ranker and seed corpus as dangerous if presented as lightweight ML; v0.1.11 plan switched to proposition-level deterministic utility with explicit corpus quality gates.

- Blast Radius: Codex and Claude visible intervention surfaces, Compass reports, benchmark mechanism evidence, and release messaging for v0.1.11.

- SLO/SLA Impact: Trust and precision SLO risk: selector metrics would be misleading even if hot-path latency stays low.

- Data Risk: No customer data exposure; the risk is provenance ambiguity and misleading quality claims from sparse labels.

- Security/Compliance: No direct security exposure; governance provenance must remain auditable and not misrepresent synthetic data as calibrated quality.

- Invariant Violated: Runtime must never claim ML calibration unless non-synthetic adjudicated corpus density gates make the artifact publishable.

- Workaround: Call the runtime deterministic_utility_v1, keep calibration loading disabled, and label the seed corpus as bootstrap/advisory only.

- Root Cause: A block-first ranker direction conflated executable regression coverage with calibrated ML quality before enough real transcript adjudication existed.

- Solution: Ship proposition-first value_engine.py, governed corpus provenance, density gates, advisory reports, adversarial evidence gates, and a runtime migration that removes signal-ranker artifacts instead of preserving compatibility.

- Rollback/Forward Fix: Forward-fix only for v0.1.11; remove stale ranker artifacts and keep runtime calibration disabled until publishable=true.

- Verification: Run value-engine unit tests, corpus validation, benchmark report tests, host-visible parity tests, and backlog/casebook validation.

- Prevention: Require origin, label source, adjudicator, rationale, duplicate groups, visibility expectation, and counts_for_calibration on every corpus case. Treat fabricated high-score/no-evidence cases, hidden-confidence inflation, missing confidence defaults, weak-evidence cases, same-label stacking, semantic duplicates with mismatched duplicate keys, non-concrete proposal actions, and candidate floods as permanent counterfactual regression coverage.

- Agent Guardrails: Do not call seed data ML-calibrated; separate deterministic runtime quality from future calibration and from odylith_on outcome proof.

- Preflight Checks: Check for existing Casebook bugs, confirm B-096 owns the intervention contract, and verify corpus quality_state remains bootstrap before claiming selector metrics.

- Regression Tests Added: tests/unit/runtime/test_intervention_value_engine.py, tests/unit/runtime/test_intervention_value_engine_benchmark.py, tests/unit/runtime/test_intervention_conversation_surface.py, tests/integration/runtime/test_intervention_visibility_browser.py, tests/unit/install/test_value_engine_migration.py

- Monitoring Updates: Advisory report exposes corpus_quality_state, calibration_publishable, duplicate rate, visibility recall, precision, recall, must-suppress accuracy, origin counts, calibration-counted case count, and latency. Runtime selection decisions also expose hard-gated count, evidence-gated count, pruned candidate count, conflict graph size, enumerated subset count, selected utility, and selector latency. Intervention stream events carry compact selected/suppressed value-decision metadata with evidence fingerprints and preserve it through assistant chat confirmation. Selector latency coverage now includes cached subset enumeration and ambient prefilter/render-call caps, so speed improvements cannot quietly trade away duplicate or support gates. Browser coverage now asserts D-038 describes the proposition ledger, conflict graph, subset optimizer, visibility broker, ruled renderer, and bootstrap adjudication report rather than the older block-first summary.

- Version/Build: v0.1.11

- Config/Flags: runtime_posture=deterministic_utility_v1; calibration_publishable=false

- Customer Comms: Do not market this as ML calibration; describe v0.1.11 as deterministic value selection with honest adjudication hooks.

- Related Incidents/Bugs: B-096, CB-122

- Code References: - src/odylith/runtime/intervention_engine/value_engine.py
- odylith/runtime/source/intervention-value-adjudication-corpus.v1.json
