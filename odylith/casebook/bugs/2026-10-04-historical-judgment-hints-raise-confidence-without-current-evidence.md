- Bug ID: CB-355

- Status: FixedPendingRelease

## Corrected source and independent proof (2026-10-04)

The source-evidence cache now observes ctime and file identity as well as size
and mtime, and refreshes parsed workstream identity/lifecycle together with its
SHA. Final expected-provenance admission owns guidance actionability through
compact transport. Seven new negative controls were red on the initial H1
bytes; the corrected source passes 53 focused tests and 15 independent
adversarial controls. Original P1s are corrected with no remaining P0/P1.
Thirty-one unchanged warm loads still require zero source-byte reads.

Correction handoff:
/private/tmp/odylith-history-memory-h1-review-corrections-handoff-20261004.json,
SHA-256 b0b6d01839467813a49813649a20dc94b3e36125dc05921b07a896535e18f145.
Independent re-review:
/private/tmp/odylith-history-memory-h1-independent-rereview-20261004.md,
SHA-256 7c08f6b87a0f0bd0f7cd8d09519403859d029aea0d545c27a4256c9732d8be7a.
Its separate packet-telemetry P2 is captured and corrected in CB-356. Final
supplement independently reports no actionable P0/P1/P2 in this bounded slice:
/private/tmp/odylith-history-memory-h1-independent-telemetry-final-20261004.md,
SHA-256 0450f67e329dd311e5478aea19c9f791b19b7c647d5ee1a7b287178d6ab33d05.
The actual complete packet is 22,473/24,000 bytes and 5,619/6,000 tokens,
retaining 12 metadata rows, seven sources and two current actionable guidance
rows under existing caps. Frozen regression and installed release proof remain
open. Preserve the original red and failed-review evidence below.

- Created: 2026-10-04

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: An executed legacy judgment-memory control supplies only a starter path, workstream ID and established status. The current-source evidence ref, source fingerprint, projection generation and evidence time are all missing, yet a matching changed file produces confidence high. The demonstrated impact is promotion of a low-signal matching workstream; no displacement of a stronger owner or new-product truth override has been demonstrated.

- Impact: Historical continuity can manufacture routing confidence without proving current source ownership, making later engineering context less trustworthy.

- Components Affected: odylith-context-engine

- Environment(s): Odylith product repo detached source-local maintainer posture on existing v0.1.15 branch.

- Detected By: Maintainer executed regression control

- Failure Signature: Legacy starter_slice without source_ref, source_fingerprint, projection generation or evidence time returns confidence=high for src/service/app.py.

- Trigger Path: Context Engine runtime-learning judgment workstream hint consumed by hot-path scope selection.

- Ownership: Context Engine judgment source, hint admission and shared scope selection.

- Timeline: Captured 2026-10-04 through `odylith bug capture`.

- Blast Radius: Codex and Claude consumers of shared Context Engine routing continuity.

- SLO/SLA Impact: Routing confidence correctness; no measured latency breach.

- Data Risk: No source data loss demonstrated; stale historical context may influence low-signal ownership.

- Security/Compliance: No security or compliance incident demonstrated.

- Invariant Violated: Historical memory must prove current source and projection compatibility before raising authority or confidence; observation time is not evidence confirmation.

- Root Cause: The legacy hint reader checks path overlap and starter status but not current source identity, lineage, fingerprint or projection generation.

- Solution: Adopt one shared memory record policy and bounded judgment source admission; retain useful historical learning without conferring current authority.

- Verification: Preserve /private/tmp/odylith-history-memory-h1-proof-20261004/red-legacy-hint.json. Initial H1 source passes 318 focused tests and six fixed indexed/fallback authority controls improve current recall/precision from 0/6 to 6/6 with wrong history promotions six to zero. Independent review then reproduces two remaining public-caller gaps: an equal-length governed source rewrite with restored mtime reuses the old source SHA because its stat cache omits ctime; generation-mismatched guidance is reference_only after final admission but retains actionable=true from earlier decoration. Both require corrected exact-source invalidation, actionability derived from final provenance admission, negative controls and independent re-review before this bug advances. Initial handoff /private/tmp/odylith-history-memory-h1-owner-handoff-20261004.json SHA-256 37d7dd9f5540d077c353cb05d23d14a505334e3d34ddc38627cf7b8b687dee0e remains historical proof rather than release qualification.

- Prevention: Authority and validity precede weighted relevance/decay; legacy missing provenance remains unknown; cache rebuilds do not reconfirm evidence. Exact-source cache invalidation must detect equal-length writes with restored mtime, and final expected-provenance admission must determine downstream actionability and compact transport.

- Related Incidents/Bugs: CB-053 closed prior TTL/fingerprint drift; B-010/B-011 completed memory work; active B-133 H1 and B-142.

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/context_engine/odylith_context_engine_runtime_learning_runtime.py
- src/odylith/runtime/context_engine/odylith_context_engine_hot_path_scope_runtime.py
