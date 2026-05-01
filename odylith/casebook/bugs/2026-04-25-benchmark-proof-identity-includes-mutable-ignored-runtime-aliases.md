- Bug ID: CB-125

- Type: Product


- Status: Closed

- Closed: 2026-04-26

- Closure Evidence: Fixed on branch `2026/freedom/v0.1.11` by filtering mutable ignored benchmark runtime aliases out of proof identity and publishing the same-head report set successfully. The selected existing v0.1.11 proof remains report `44f2a3d83d2c9975`; the release-maintainer decision on 2026-04-26 is to reuse that report rather than rerun the benchmark after later release-UX-only commits.

- Created: 2026-04-25

- Severity: P1

- Reproducibility: High


- Description: Benchmark publication could reject a valid same-head proof because the proof report identity fingerprint included mutable ignored runtime benchmark aliases written after the proof run.

- Impact: README benchmark publication and release-proof closeout could be blocked after an otherwise valid proof, pushing maintainers toward unnecessary reruns or stale-proof interpretation.

- Components Affected: benchmark

- Environment(s): Odylith product repo maintainer mode on branch 2026/freedom/v0.1.11 during sharded proof, diagnostic, and README publication.

- Detected By: Publication attempt after merged proof and diagnostic benchmark runs, followed by focused tree-identity and publication tests.

- Failure Signature: odylith_benchmark_publication refused the live proof as stale because the report identity snapshot included ignored .odylith/runtime/odylith-benchmarks latest alias paths that changed after the report was generated.

- Trigger Path: python -m odylith.runtime.evaluation.odylith_benchmark_publication --repo-root . --live-report <proof-report> --diagnostic-report <diagnostic-report> after a proof and diagnostic pair on the same head.

- Ownership: Benchmark tree identity and publication authority contract.

- Timeline: Captured on 2026-04-25 during v0.1.11 benchmark reproof after the publication refusal was fixed and the same-head proof was regenerated.

- Blast Radius: README benchmark snapshots, latest summary JSON, proof and diagnostic graphs, release-proof gating, and maintainer benchmark triage.

- SLO/SLA Impact: Release proof publication could stop on false current-tree drift and burn hours of live benchmark capacity.

- Data Risk: Low product data risk, high benchmark-governance truth risk.

- Security/Compliance: No direct security or compliance impact.

- Invariant Violated: Benchmark proof identity must derive from tracked source truth and explicit report snapshot paths, not mutable ignored runtime aliases that are allowed to change after report generation.

- Root Cause: The proof identity path collector included mutable ignored benchmark runtime aliases from .odylith/runtime/odylith-benchmarks instead of filtering identity to tracked source truth and explicitly snapshotted paths.

- Solution: Filter mutable ignored runtime benchmark overlays out of benchmark tree identity, keep explicit snapshot paths stable, and move the identity helper out of the oversized runner module.

- Rollback/Forward Fix: Forward fix only; reverting would reopen false-stale publication failures.

- Verification: Focused publication and graph tests passed with 27 passed; focused tree-identity and hotfile tests passed with 9 passed; final same-head proof report 44f2a3d83d2c9975 and diagnostic report 9dcae95d5bb62c75 published successfully.

- Prevention: Keep tree-identity filtering covered by unit tests and audit publication failures for ignored runtime alias pollution before rerunning expensive proof.

- Agent Guardrails: Do not treat a publication identity mismatch as a real source drift until the compared path set has been checked for ignored runtime benchmark aliases.

- Preflight Checks: Inspect benchmark tree identity helpers, publication report matching, .odylith/runtime/odylith-benchmarks aliases, and CB-116 before changing publication authority again.

- Regression Tests Added: tests/unit/runtime/test_odylith_benchmark_tree_identity.py and publication coverage in tests/unit/runtime/test_odylith_benchmark_publication.py.

- Monitoring Updates: Final report publication now leaves latest-summary.v1.json tied to report 44f2a3d83d2c9975 without requiring mutable runtime alias identity.

- Version/Build: v0.1.11 benchmark publication hardening on head 1cfca107.

- Config/Flags: proof shards capped to four parallel workers, same-head diagnostic benchmark, and README publication command using explicit live and diagnostic report paths.

- Customer Comms: Public benchmark claims should cite the regenerated report ids, not the refused pre-fix publication attempt.

- Related Incidents/Bugs: CB-116

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_tree_identity.py
- src/odylith/runtime/evaluation/odylith_benchmark_runner.py
- src/odylith/runtime/evaluation/odylith_benchmark_publication.py
- tests/unit/runtime/test_odylith_benchmark_tree_identity.py

- Runbook References: - odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md

- Fix Commit/PR: 2586dc71 and 1cfca107 on branch 2026/freedom/v0.1.11
