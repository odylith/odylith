- Bug ID: CB-116

- Type: Product








- Status: Open

- Created: 2026-04-15

- Severity: P1

- Reproducibility: High


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

- Release Note: On 2026-05-01, v0.1.12 candidate proof passed 3373 tests and built the release wheel, then benchmark compare failed closed because there was still no current-tree authoritative proof report. The v0.1.12 maintainer override records benchmark proof and compare as advisory for that exact recovery release instead of weakening this invariant.

- Release Note: On 2026-05-04, the maintainer explicitly waived full benchmark
  runs for the v0.1.14 GA release. The tracked v0.1.14 maintainer override
  keeps benchmark proof and compare advisory for that exact version while the
  release relies on Product Governed Harness Turn Gate formal-model truth,
  migration-gate coverage, browser-surface proof, install and runtime migration
  tests, topology/guidance/discipline validation, and release-candidate proof.
  Do not narrate v0.1.14 as benchmark re-proved.

- Code References: - src/odylith/runtime/evaluation/benchmark_compare.py
- src/odylith/runtime/evaluation/odylith_benchmark_publication.py

## Metadata is not source identity (2026-10-15)

After the first canonical A publication, restoring only its twelve generated
outputs to the same clean a160 Git commit leaves the original report rejected.
All non-overlay identity fields match; the overlay fingerprint changes from
e9a80c8195627e2e46121a31598d890d5413709901ab3007e5fbe213d8b869e1
to c672642371673b621f7be184faa940545d3acc31d632069841797fafb8c291ea.
The existing owner uses cache signatures containing modification times rather
than content. Original reports remain unchanged and the refusal is retained.
Independent review recommends a benchmark-local, versioned content identity.
A legacy reconciliation may accept only the same clean commit with every
consumed overlay input proven tracked and byte/mode-identical. Directory
prefixes cannot authorize ignored or untracked descendants. Missing, unsafe
or unresolved inputs must refuse. Keep all other authority checks strict; no
report edits, timestamp restoration, predicate bypass or source-proof waiver.
A remains measurement evidence for a160, and final H/B remains required.

The targeted a160 custody check finds 438 ignored descendants beneath the
consumed src/odylith/runtime directory, chiefly Python bytecode. The historical
metadata fingerprint does not retain their bytes, so clean Git alone cannot
recertify this legacy overlay after restoration. Do not add an unused or
permissive legacy reconciliation path. Preserve exact legacy validation and
use a versioned content-and-mode fingerprint, including directory inventory
and missing inputs, for future reports. The original A measurement and first
publication remain preserved; current regenerated publication needs fresh
content-bound proof. No quality threshold or semantic release floor changes.

The two-file correction passes 41 identity tests and 210 affected benchmark
tests. New reports store `content-v1:<sha256>` in the existing fingerprint
field, which the runner already preserves. Content, modes, explicit absence
and full directory inventory determine the hash; modification times and
absolute checkout paths do not. Legacy reports retain their original exact
metadata check. Unknown markers and unsafe or unreadable inputs refuse.
Independent review is clear on the exact final bytes; its separate 41-test
run also passes. Fresh current-source proof remains required.
