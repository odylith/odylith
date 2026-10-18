- Bug ID: CB-364

- Status: Open

- Created: 2026-10-15

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The release comparator subtracts each release's Odylith-minus-raw quality advantage and labels that difference as product quality regression. Completed actual v0.1.14 a9e009b5d75cc51b and v0.1.15 A81889b62b36af1fc both have conservative Odylith critical recall0.979 and overall recall0.992. Raw critical recall rises0.772 to0.797, so the comparator reports a false critical regression of0.025 and blocks. All82 per-case Odylith recall values are unchanged. A companion discovery defect allows an interrupted failed receipt with no evaluated summaries to win baseline selection when timestamps tie.

- Impact: Release gating can falsely reject unchanged product quality and can miss genuine product decline when the raw baseline declines further. Interrupted execution can also supply a nonblocking baseline comparison.

- Components Affected: benchmark

- Environment(s): Product maintainer detached source-local candidate a160260365815bb9773fbd2aac1fe0bbafebd7b1; clean full warm/cold proof and authentic completed v0.1.14 predecessor.

- Detected By: Canonical benchmark compare after full A; independent archived-report review and all82 per-case recall comparison.

- Failure Signature: Canonical completed14 comparison exits2 and reports critical required-path recall regressed by0.025 despite Odylith0.979 to0.979. Earlier canonical comparison selected interrupted4b3ecb8eb493c1fa, evaluated_mode_count0, instead of completed a9. Both original outputs are retained unchanged.

- Trigger Path: odylith benchmark compare --repo-root . --baseline last-shipped --json

- Ownership: Benchmark release comparison quality semantics and completed-baseline eligibility.

- Timeline: Captured 2026-10-15 through `odylith bug capture`.

- Blast Radius: Release qualification, benchmark regression decisions and public comparison claims.

- SLO/SLA Impact: Blocks release preparation on a false regression and risks undetected true quality regressions.

- Data Risk: Original measurement bytes remain intact; comparison authority and interpretation are at risk.

- Security/Compliance: No direct security or compliance defect established.

- Invariant Violated: Cross-release product-quality checks must compare conservative absolute Odylith measurements using the existing thresholds, while contemporary Odylith-versus-raw hard gates remain intact. Incomplete execution cannot authorize a baseline comparison.

- Workaround: Operational retention of the interrupted receipt exposed the second defect without changing its bytes. The original receipt is now restored beside the completed reports for corrected selection proof. Both original comparison outputs remain unchanged. Final H/B qualification is still required.

- Root Cause: The comparator maps release quality checks to already relative summary delta fields, then subtracts them again. Baseline eligibility checks full selection and cache metadata but not completed observations; stable filename order breaks tied generated_utc in favor of an interrupted receipt.

- Solution: Compare conservative absolute Odylith quality across releases with unchanged thresholds and directions. Retain On-minus-raw advantages and their change as labeled diagnostics, preserve all within-release gates and existing latency/token checks, and fail closed on missing absolute measurements. Exclude incomplete execution from eligible history while retaining completed HOLD observations.

- Timing Classification: Cross-release live-proof timing and full-session-token deltas remain visible warnings at their existing `10/20ms` and `20/40-token` levels. They are not release failures because the matched pair measures shared benchmark time and full host-session cost, not solo-user latency or initial prompt size. This does not alter the values, thresholds, within-run measurements, or original failed comparison.

- Rollback/Forward Fix: Forward fix in existing release settlement; final H/B proves corrected source.

- Verification: The corrected five-file slice passes 148 focused tests and independent review. It covers unchanged On with improved raw, genuine On decline hidden by worse raw, missing or invalid measurements, interrupted history, completed HOLD, canonical publication round-trip, and in-range stored-score tampering. Canonical replay of unchanged A and actual14 reports with the original interrupted receipt present selects a9e009b5d75cc51b, exits0, and returns a nonblocking warning for baseline HOLD. Critical recall and overall recall changes are zero; validation success changes by +0.027. The original exit2 output is retained. Final H/B must prove the corrected source before release closure.

- Independent Review: `release-timing-policy-independent-review.md` (SHA-256 `51beab4e39d2b5b81637c1327f5e53b47bb54b0fd29b48b3fa71ce331198af13`) confirms the policy conflict and the bounded correction: preserve absolute quality, fairness, completion, identity, candidate acceptance, and `within_budget_rate >= 0.80` as blockers; preserve timing/token measurements and thresholds as warnings. New H, CI, one full 82-scenario warm/cold B, and canonical predecessor comparison remain required. No override, threshold change, raw replay, or reinterpretation of the retained failed output is allowed.

- Implementation Evidence: The bounded comparator change preserves the exact `10/20ms` and `20/40-token` thresholds and emits nonblocking diagnostic warnings for their cross-release breaches. `109` comparator tests, `10` CLI/lane tests, and `13` acceptance tests pass (`132` distinct focused tests). Quality decline, `within_budget_rate` below `0.80`, fairness findings, identity or completion failures, stale reports, invalid measurements, and incomplete history still block. The retained failed comparison remains SHA-256 `6bf85c84bf5072f56c0a9450dff746d394519afdb142e435d3515daaaf474ffc`; this focused proof is not new H, CI, or B credit.

- Final Review: `release-comparison-policy-final-review.md` (SHA-256 `5a30ba7274827449fc05d9d523ab4cd29a3b2aa1285dcb8c3b41dbedccc73a7d`) reports no findings. It confirms the implementation keeps numeric thresholds and diagnostics visible while preserving quality, budget, fairness, identity, and completion blockers.

- Agent Guardrails: Do not alter measurement bytes, timestamps, criteria or thresholds; do not filter completed quality failures or relabel the original comparison. A remains measured proof of a160 only. Preserve two-case/four-supporting-path corpus disclosure.

- Version/Build: 0.1.15 candidate a160260365815bb9773fbd2aac1fe0bbafebd7b1

- Related Incidents/Bugs: CB-032; CB-116; B-141

- Code References: - src/odylith/runtime/evaluation/benchmark_compare.py

- Runbook References: - odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md

## Publication review (2026-10-15)

Independent review of the canonical A publication finds three copy defects: both
quality-frontier charts retain a fixed 60-point caption despite 82 scenario
pairs, the tables assume a missing registered baseline instead of reporting only
their supplied proof, and an archive paragraph labels v0.1.11 current. Remove
these stale claims in the existing graph/publication generators and README.
Preserve the measured values, graph style, diagnostic HOLD, original failed
comparison and final H/B requirement. Rebuild from the same immutable reports
and verify the graph/publication contracts before checkpointing.
