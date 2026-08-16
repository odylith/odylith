- Bug ID: CB-326

- Status: Open

- Created: 2026-08-16

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The installed matrix baseline scanned only authoritative declared leakage sentinels while generated-artifact scoring could emit the wider source-grounded candidate set. A platform-native phrase therefore failed post-readback leakage despite existing before product execution.

- Impact: A correct 24-case installed replay is reported failed, blocking release progression and the authorized replacement holdout.

- Components Affected: release

- Environment(s): 0.1.15 exact local release assets from commit 8c05f74213cc2a1c91bcde2ffbfbe8c6ac3ad0ed, disclosed-v3 regression campaign

- Detected By: Installed greenfield pre-confirm matrix

- Failure Signature: Unicode résumé review scored 0/10 only because docs/runbooks/odylith-migration.md:11 leaked pre-existing phrase confirms success

- Trigger Path: greenfield_preconfirm_matrix.py --campaign-phase disclosed-v3-regression with frozen disclosed v3 annotations

- Ownership: Release evaluator leakage-custody baseline

- Timeline: Captured 2026-08-16 through `odylith bug capture`.

- Blast Radius: Installed matrix cases with a grounded declared sentinel whose generated output also contains a platform-native supplemental source phrase

- SLO/SLA Impact: Delivery SLO impact: release readiness is blocked; no production runtime outage

- Data Risk: Domain risk: none. Delivery risk: false release stop. Operational risk: matrix rerun cost only. No data mutation or loss.

- Security/Compliance: Compliance, policy, privacy, accessibility, and safety assessment: no direct impact. Strict leakage detection remains fail-closed for genuine post-baseline findings.

- Invariant Violated: Every term eligible for post-generation leakage scoring must be checked against platform custody before product execution

- Root Cause: platform_baseline_required_terms used case_leakage_terms while case_generated_leakage_terms used case_leakage_term_candidates

- Solution: Baseline-scan the same source-grounded candidate set, keep exact-term suppression, remove the dead raw-required-term helper, and retain strict declared/source-provenance controls

- Rollback/Forward Fix: Forward fix evaluator only; product wheel remains unchanged

- Verification: Exact regression plus full evaluator and security/proof suites, followed by full installed disclosed-v3 replay from case 1

- Prevention: Pin candidate-space symmetry and genuine leakage negative controls

- Agent Guardrails: Do not delete platform prose, weaken the scanner, suppress super/subphrases, or classify raw quality anchors as leakage sentinels

- Preflight Checks: Frozen contract and input hashes must pass; replacement holdout remains sealed

- Regression Tests Added: test_platform_baseline_filters_native_supplemental_candidates_with_declared_sentinel

- Version/Build: 0.1.15 / 8c05f74213cc2a1c91bcde2ffbfbe8c6ac3ad0ed

- Related Incidents/Bugs: CB-272, B-142

- Code References: - scripts/release/greenfield_matrix_leakage.py
- tests/unit/install/test_greenfield_matrix_evaluator_regressions.py
