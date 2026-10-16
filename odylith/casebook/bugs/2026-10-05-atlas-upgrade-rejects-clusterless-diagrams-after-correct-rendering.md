- Bug ID: CB-358

- Status: Open

- Created: 2026-10-05

- Severity: P1

- Reproducibility: Always

- Type: Deployment

- Description: The populated published-v0.1.14 to candidate-v0.1.15 witness failed after activation because Atlas mistook unused cluster CSS for an actual cluster. The correctly rendered diagram had six polished nodes and no cluster elements. All eleven authored file modes remained unchanged; ten of eleven raw file byte sequences remained unchanged. The only catalog leaf change was the pre-existing compiler-owned render_source_fingerprint. The original failed consumer, ledgers and evidence remain preserved.

- Impact: A valid populated consumer cannot complete its supported hosted upgrade; runtime activation finishes before Atlas verification fails.

- Components Affected: odylith

- Environment(s): macOS full-memory consumer; verified published v0.1.14 fae446995e13e12409e50f944a336dbc846db90a to clean candidate d0021184faba41b8fac887ce107ee452d8dc2722.

- Detected By: One genuine populated migration witness, with six governance source families and eleven retained files.

- Failure Signature: Atlas render-surface migration did not verify after apply

- Trigger Path: Published v0.1.14 launcher refuses the unregistered v0.1.15 target, then the supported candidate hosted installer continues in the same populated consumer.

- Ownership: Odylith installer Atlas render-surface migration predicate.

- Timeline: Captured 2026-10-05 through `odylith bug capture`.

- Blast Radius: Populated consumers with valid clusterless Mermaid SVGs whose unused style sheet contains legacy cluster tokens.

- SLO/SLA Impact: Release migration and installation readiness remain blocked.

- Data Risk: Authored source meaning and modes preserved; one existing compiler-owned catalog render fingerprint updated. Consumer and nonterminal evidence retained.

- Security/Compliance: No authority expansion or trust bypass; normal signature, checksum, provenance and SBOM checks used.

- Invariant Violated: Migration verification must inspect actual SVG elements and must accept a correctly rendered supported diagram.

- Root Cause: _svg_cluster_needs_polish_from_inspection falls back to raw stylesheet tokens when the XML contains no cluster elements; unused CSS is misclassified as a rendered cluster.

- Solution: Use the existing XML class inspection with explicit parse validity; inspect real cluster elements and refuse malformed XML. Proposed correction reduces the source file by one line.

- Verification: Original two focused controls fail and the real legacy cluster control passes. Independent external-copy review passes fifteen controls, including malformed XML refusal and the actual retained SVG. Application, target tests and installed recovery remain pending. Evidence: /private/tmp/odylith-v20-populated-migration-proof-20261004; /private/tmp/odylith-v20-atlas-populated-migration-diagnosis-20261004.json; /private/tmp/odylith-v20-atlas-proposed-correction-review-20261004.json.

- Prevention: Cover valid zero-cluster SVGs with unused legacy CSS, real legacy clusters and malformed XML. Do not weaken palette or source semantics.

- Related Incidents/Bugs: B-145, B-142, CB-338, CB-347

- Code References: - src/odylith/install/atlas_surface_migration.py

## Retained correction boundary (2026-10-05)

The original source hash is
`8b76a92cd7a2b1c41d059d62d9f3d705c613f85df3fe57072382ac34ec7e7cd5`;
the independently reviewed proposed source hash is
`69cbacd54f8e524b1351513df7a36f799e5e3f5ffea73c9039383a3adce9d125`.
The 15 external-copy controls pass: seven existing characterizations, the two
original clusterless failures, the real legacy-cluster control, three malformed
XML refusals, a clusterless legacy-node refusal and the actual retained SVG
inspection. The review is CLEAR only within that proposed-code scope. Receipt:
`/private/tmp/odylith-v20-atlas-proposed-correction-review-20261004.json`, SHA-256
`f97f72edad6526dc108534fb30831fd64960cf92757ca8c2b752e956aae774a2`.
The consumer and original failing controls remain unchanged. Post-application
target tests and supported installed recovery remain pending; keep this bug Open.

B-145 now names only the already-derived `render_source_fingerprint` leaf as a
possible change, requiring exact selected-diagram identity, exact diff and
recomputed source/theme value while preserving every authored field and all
modes. The original failed witness still has raw-byte preservation of 10/11 and
mode preservation of 11/11. No whole-catalog exemption, recovered installation,
five-class migration approval or release success is inferred.

## Post-application bounded checks (2026-10-05)

Root applied the reviewed Atlas correction and CI test-import correction.
With `PYTHONPATH` unset, 33 actual Atlas/CI checks pass in 2.99 seconds and
90 adjacent installation/migration checks pass in 3.60 seconds. Logs:
`/private/tmp/odylith-v20-concrete-corrections-target-tests-20261004.log`, SHA-256
`88fd61e0c2bd8a6f3de4277d18d8784ad66e5910e169d996a4f34fcd33164b4f`, and
`/private/tmp/odylith-v20-atlas-migration-neighbors-20261004.log`, SHA-256
`3e19cb5b7fa67596ccafec9c85abe62aa74054885036291c9f5160176688aa17`.
These 123 application checks are separate from the earlier 15 proposed-code
controls. No new complete 8,410-test freeze, Ubuntu pass or installed recovery
has run. CB-358 remains Open and all five migration classes remain unapproved.
