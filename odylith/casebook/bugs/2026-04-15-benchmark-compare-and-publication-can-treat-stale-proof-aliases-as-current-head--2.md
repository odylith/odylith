- Bug ID: CB-116

- Status: Open

- Created: 2026-04-15

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Benchmark compare and publication can continue to reason from an older latest-proof.v1.json report or tracked summary even after the repo head has moved forward and only diagnostic or interrupted proof evidence exists for the current tree. That makes the benchmark lane sound more authoritative and current than it is.

- Impact: Maintainers can read stale proof posture as if it were current-head benchmark truth, which poisons release gating, benchmark storytelling, and benchmark recovery decisions.

- Components Affected: benchmark

- Environment(s): Odylith product repo maintainer mode on detached source-local posture with current-head benchmark reruns, interrupted proof shards, and an older latest-proof.v1.json alias still present.

- Detected By: Maintainer inspection of .odylith/runtime/odylith-benchmarks/latest-proof.v1.json, current-head diagnostic report fc45775a1a4761d3, interrupted proof reports, and the compare/publication codepaths.

- Failure Signature: latest-proof.v1.json still points at an older hold report on commit 73e612628777c2ecc2aaf12c15a3570b54880c0f while the current head 735265e99c0873b5ad195f2aa1e8c6acc3560197 only has current-head diagnostic proof and interrupted proof shard artifacts. Compare/publication code still has stale-summary fallback paths that can blur that boundary.

- Trigger Path: Run current-head benchmark reruns until proof is interrupted or incomplete, leave an older latest-proof.v1.json alias in place, then inspect benchmark compare/publication behavior without a fresh current-head proof alias.

- Ownership: benchmark compare and publication authority contract

- Timeline: Captured 2026-04-15 through `odylith bug capture`.

- Blast Radius: Benchmark compare, proof publication, benchmark docs, release-gating posture, and maintainer benchmark triage.

- SLO/SLA Impact: Release-proof confidence and benchmark publication trust degrade because the benchmark lane can overstate what is actually current-head authoritative.

- Data Risk: Low product-data risk, high benchmark-governance and release-proof trust risk.

- Security/Compliance: None directly.

- Invariant Violated: Current-head benchmark compare and publication must not treat stale proof aliases or tracked summaries as authoritative candidate proof for the current repo tree.

- Solution: Keep compare and publication fail-closed on current-tree authority: explicitly mark stale runtime reports as stale, refuse tracked-summary fallback for current-head release gating, and surface current-tree mismatch clearly until a fresh current-head proof report exists.

- Verification: Add unit coverage for stale runtime report handling in benchmark compare/publication and prove current-tree mismatch is reported as unavailable or stale instead of current candidate proof.

- Prevention: Preserve exact tree identity checks across candidate proof selection, keep stale-runtime markers explicit in summaries, and avoid passive fallback paths that can silently masquerade as current-head proof.

- Agent Guardrails: Do not describe benchmark proof as current-head authoritative unless benchmark_report_matches_current_tree(...) holds for the selected proof report.

- Regression Tests Added: Benchmark compare tests for stale proof alias handling and publication tests for stale current-tree warnings.

- Related Incidents/Bugs: CB-113

- Code References: - src/odylith/runtime/evaluation/benchmark_compare.py
- src/odylith/runtime/evaluation/odylith_benchmark_publication.py
