Status: In progress
Created: 2026-10-04
Updated: 2026-10-04
Backlog: B-133

# Current Authority and Useful History in Memory

## Goal

Improve Retrieval memory and Judgment/session memory with one shared policy
that preserves authentic, accurate, current, useful evidence and historically
useful decisions and failures. The operator explicitly authorizes this first
B-133 wave while Greenfield B-142 converges. Significant improvement requires
measured correctness, useful later recall and bounded cost on fixed cases.

## Evidence and Existing Owners

The source-grounded history-policy audit identifies existing timestamps,
freshness buckets, source trust, projection fingerprints/generations, workstream
lineage, current-source selection and proof falsification memory. Reuse them.
Judgment starter hints presently omit current-source/provenance admission and
can strengthen low-signal choices. Snapshot rebuilds refresh last_seen_utc even
without new confirming evidence. CB-355 retains an executed red control: a
source-less legacy starter hint raises a matching low-signal workstream to high
confidence. No displacement of a stronger owner or old-product-contract
override has been demonstrated.

Audit: /private/tmp/odylith-history-authority-policy-audit-20261004.md,
SHA-256 11afe51cdffc6b28f40dde33cbb7369855626762b08b6f12613410dda8ca240d.
CB-053 is the closed prior TTL/fingerprint failure and must not be repeated.
The initial live repo reported compiler snapshots/repo-scan fallback because
declared LanceDB/PyArrow/Tantivy dependencies were absent. Restoring the declared
dependencies enables a diagnostic Tantivy query; final settled readiness and
indexed/fallback parity still require proof. Vespa remains disabled. Do not
infer memory accuracy from metadata, index activation or file counts.

## Decisions

- Governed source remains authoritative. Derived records retain source refs,
  evidence time and existing generation/fingerprint provenance.
- Make record role and validity explicit: current truth, historical learning
  and observations have different uses; explicit supersession, rejection or
  refutation prevents a record from becoming current policy.
- Missing legacy metadata stays unknown. Age alone cannot decide truth,
  supersession, confirmation or source authority.
- Admit authority and validity before ranking relevance, evidence strength and
  freshness. A weighted historical score cannot outrank current valid source.
- Current explicit intent and active safety/proof constraints keep their
  authority regardless of age. Useful failed mechanisms remain discoverable
  as learning evidence rather than instructions to repeat the failed path.
- Separate a cache observation timestamp from evidence confirmation time.
  Rebuilding a snapshot does not reconfirm a remembered fact.
- Use one Context Engine policy across producer, retrieval and hint admission;
  Memory Contracts preserves compact results without deciding their meaning.
- Preserve shared-only ambiguity, session-intent non-replay, source secrecy,
  source fingerprints and all Greenfield source/receipt/transaction boundaries.

## Execution Wave H1

- [x] Add a bounded shared record policy with explicit metadata, explainable
      weighting and decay within authority classes.
- [x] Adopt it in judgment synthesis and the existing starter-hint reader,
      preserving evidence time and validating current source/lineage before
      routing confidence can increase.
- [x] Carry metadata and provenance through snapshots, retrieval and compact
      packets. Exercise both compiler fallback and local-backend contracts.
- [x] Improve actual record selection/recall, not only timestamp display or a
      helper disconnected from live callers.
- [x] Prove positive useful historical retrieval and current continuity as well
      as stale/rejected/refuted/superseded refusal; keep legacy unknown honest.
- [x] Independently review current-authority precedence and negative controls.
- [x] Preserve honest Atlas review scope during the owned H1 diagram update;
      correct CB-357 and recover only the root-owned accidental marker changes.
- [ ] Settle affected Registry/Atlas/Compass and release/migration proof after
      actual contract changes; checkpoint on the existing branch.

## Impacted Areas

- Context Engine judgment synthesis, runtime learning and scope selection.
- Context Engine retrieval/projection owners where the shared policy is used.
- Memory Contracts compact transport and source/provenance preservation.
- Existing Memory Backend inputs and readiness contracts, with no automatic
  remote activation or provider calls on the hot path.
- B-142 shared non-regression and useful-history release requirements.
- Atlas authoring/owned refresh must not manufacture unrelated review evidence.

## Validation

Use fixed evidence and inspect real producer -> snapshot -> retrieval -> compact
packet -> later decision behavior. Preserve original red results and source
hashes. Measure critical recall, precision, stale-authority mistakes, preserved
failure evidence, false confidence promotions, continuity, packet size, bounded
reads and latency. Compare the same cases with the old behavior; do not rewrite
expected truth to match output or use a larger packet as the success metric.

Required controls: newer historical guidance versus older active constraint;
explicit rejected/refuted/superseded records versus current accepted source;
unknown legacy metadata; changed fingerprints/generations; contradictory current
claims; rebuild without new evidence; current valid continuity; shared-only
ambiguity; real later use of a relevant failed mechanism. No model/provider,
subagent, broad scan or projection expansion is added to admission hot paths.

Existing test families: test_odylith_memory_areas,
test_context_grounding_hardening, test_context_engine_shared_support_selection,
test_context_session_resumption, test_derivation_provenance,
test_tooling_memory_contracts and existing retrieval/benchmark contracts.
Fresh measured benchmark and installed proof remain required for release claims.

### Settled Source Proof, 2026-10-04

Owner handoff: /private/tmp/odylith-history-memory-h1-owner-handoff-20261004.json,
SHA-256 37d7dd9f5540d077c353cb05d23d14a505334e3d34ddc38627cf7b8b687dee0e.
The fixed source passes 318 focused tests in 85.21 seconds across actual memory
backend, compiler fallback, compact transport/redaction, retrieval and session
resumption. Six identical deterministic controls compare older active source
constraints with newer completed failures across Radar, plans and Casebook, using
both actual indexed and compiler transports: current recall/precision at one
improves from 0/6 to 6/6 and wrong history promotions decrease from six to zero.
The unsupported legacy hint is refused; legitimate current continuity and useful
past failure recall remain available. Memory-only refresh retains its original
confirmation rather than renewing itself. Thirty-one warm continuity reads
perform zero source-byte reads.

Observed local median latency is 0.868 to 1.011 ms for indexed retrieval and
0.137 to 0.339 ms for compiler retrieval. Three compact policy/provenance records
add 2902 bytes; packet caps and redaction remain required. These are fixed local
controls, not universal semantic accuracy, installed activation, a production SLA
or whole-platform qualification. Independent review, complete frozen runtime and
install validation, installed migration and release proof remain open.

Independent review reproduces two public-caller gaps in that initial handoff:
same-length source modification with restored mtime bypasses the stat-based
source cache, and generation-mismatched guidance retains actionable instructions
after final admission marks it reference-only. CB-355 retains these failed
mechanisms. The owner is correcting both with executed negative controls;
initial focused proof is not release qualification and re-review is required.

### Corrected Source and Independent Review

Both original P1 gaps are corrected: source signatures include ctime/file
identity and parsed source identity/lifecycle refresh together; final
expected-provenance admission determines downstream instruction actionability.
Seven controls were red on the initial source. The correction passes 53 focused
tests and 15 independent adversarial controls, preserving legitimate current
continuity, identical atomic replacement and 31 warm reads with zero source
bytes. Exact correction handoff:
/private/tmp/odylith-history-memory-h1-review-corrections-handoff-20261004.json,
SHA-256 b0b6d01839467813a49813649a20dc94b3e36125dc05921b07a896535e18f145.

The real bootstrap assembler obeys existing aggregate limits while retaining
admitted records. Its exposed telemetry mismatch is corrected under CB-356 in
two lines, with a real-estimator characterization test. Final independent
supplement passes both required controls and reports no actionable P0/P1/P2:
/private/tmp/odylith-history-memory-h1-independent-telemetry-final-20261004.md,
SHA-256 0450f67e329dd311e5478aea19c9f791b19b7c647d5ee1a7b287178d6ab33d05.
The complete serialized packet is 22,473/24,000 bytes and 5,619/6,000 tokens;
12 metadata rows, seven distinct sources and two current actionable guidance
rows survive existing trimming. Complete frozen regression, installed migration
and release remain open; source admission is not transactional filesystem
tamper-proofness or universal semantic entailment.

### Adjacent Governance Preservation: CB-357

The actual D-025 metadata update renders the new memory flow correctly but its
owned refresh silently performs global --all-stale acknowledgement. The catalog
was clean before that root-owned operation; 35 unrelated rows change only dates
or watched-content review fingerprints. Exact current and HEAD catalogs are
retained privately before recovery. This contradicts the explicit selected
update contract and is captured under CB-357 before corrective work.

Forward validated selected diagram IDs through existing authoring, owned
refresh, auto-update, scoped freshness checks and cache identity. Preserve
authored review dates in the selected authoring path; direct explicit automatic
and global sync retain their existing acknowledgement behavior. All projection,
memory and render engines remain active. Root will restore only its catalog
from verified HEAD, then replay D-025 through the corrected CLI with the actual
review date, proving every unrelated row remains exactly unchanged. No catalog
JSON is hand-authored and no leaf owns that recovery.

This is a bounded safety exception for the existing 2842-line sync owner and
1014-line auto-update owner. It carries one selection scope through existing
owners, adds no refresh framework and does not authorize unrelated growth or a
whole-file decomposition claim. Meaningful selected/batch/full-sync/cache and
failure controls precede independent review. Diagnosis:
/private/tmp/odylith-atlas-update-review-scope-diagnosis-20261004.md.

The first implementation passes 166 checks. Independent actual-chain review
finds its second authoring caller, `atlas scaffold`, still uses global review
scope. All three unrelated fixture rows are falsely acknowledged before a
render failure; retry advice is also global. Extend the same validated scope
to this caller and characterize the real chain before root recovery. Initial
failed review is retained at
/private/tmp/odylith-atlas-update-scope-independent-review-20261004.md,
SHA-256 19e1d08172a57bc8b30490da4aa9e3e467e52771720f70ff2a2db0170289bdee.

The same scope is now adopted by scaffold with one source line. Final
independent review passes 10 actual-chain and seven direct/global/cache checks,
plus its unchanged original reproduction, with no actionable P0/P1/P2:
/private/tmp/odylith-atlas-update-scope-independent-rereview-20261004.md,
SHA-256 6a1f8379073950a3e8275ea30847dac6a8322f63349758348933e6cea693fc73.
Root's hash-guarded catalog recovery and corrected D-025 replay succeed;
D-025 is the only changed entry and every unrelated object equals HEAD.
Reviewed MMD/SVG/PNG hashes remain unchanged. Exact recovery receipt:
/private/tmp/odylith-atlas-update-scope-recovery-20261004/receipt.json.
CB-357 is FixedPendingRelease. Full frozen and installed proof remain open.

### Bounded Ownership and Size Pressure

H1 moves authority/ranking into one 266-line policy and current judgment evidence
admission into one 159-line owner, adopted by all touched producers and readers.
It removes 257 duplicate backend document-construction lines by adopting the
existing compiler table builder. The 15 source adopters total a net 292-line
increase; exact before/after hashes and line counts are retained in the handoff.
The corrected judgment owner is 167 lines; the final 15-adopter net delta is
308 lines. Packet-telemetry correction replaces two reads without source growth.

Existing oversized callers stay under this active H1 decomposition boundary:
runtime learning decreases 1942 to 1902 lines and the memory backend decreases
1831 to 1603. Projection search increases 2765 to 2806, hot-path scope 1571 to
1588, and compact contracts 1265 to 1301 through narrow shared-policy adoption.
Those callers delegate the new authority decision to its actual owner; they do
not retain a competing local policy. This is a bounded exception for the proven
source-admission correction. Further unrelated growth is forbidden before their
remaining search/selection, scope resolution and transport phases receive owned
decomposition with characterization proof. H1 does not claim those entire files
or the repository are decomposed.

## Risks and Mitigations

- Risk: a recent cache timestamp disguises old evidence. Mitigation: retain
  confirmed evidence time separately and require current derivation admission.
- Risk: numerical rank promotes invalid history. Mitigation: authority/validity
  controls eligibility before weighted relevance and age.
- Risk: old valid constraints disappear. Mitigation: active current constraints
  do not lose authority through decay; test them against recent weak context.
- Risk: source and compact metadata drift. Mitigation: use one shared owner and
  prove round-trip preservation on live callers and both retrieval contracts.
- Risk: scope growth delays Greenfield. Mitigation: H1 is the authorized memory
  policy/selection wave; wider collaboration annotations remain separate.

## Traceability

### Runbooks

- `docs/runbooks/odylith-governance.md`

### Code References

- `src/odylith/runtime/context_engine/memory_record_policy.py`
- `src/odylith/runtime/context_engine/judgment_memory_records.py`
- `src/odylith/runtime/context_engine/odylith_context_engine_judgment_memory_runtime.py`
- `src/odylith/runtime/context_engine/odylith_context_engine_runtime_learning_runtime.py`
- `src/odylith/runtime/context_engine/odylith_context_engine_hot_path_scope_runtime.py`
- `src/odylith/runtime/memory/tooling_memory_contracts.py`

### Developer Docs

- `docs/CONTEXT_ENGINE.md`
- `odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md`
- `odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md`
- `odylith/registry/source/components/odylith-memory-contracts/CURRENT_SPEC.md`
