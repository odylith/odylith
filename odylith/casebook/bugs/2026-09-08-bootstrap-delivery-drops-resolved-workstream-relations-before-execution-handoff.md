- Bug ID: CB-333

- Status: FixedPendingRelease

- Fixed In: 0.1.15

- Created: 2026-09-08

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The native-Claude-published structural Greenfield project resolves B-001, test-boundary-1 and D-001/D-002 through the public context CLI. Bootstrap retains the resolved dossier through finalization but its delivered view drops that dossier and builds an Execution handshake with no target components. Session resume retains scope after CB-332 but does not repair this separate delivery boundary.

- Impact: A consumer resumes the accepted project without its selected component and architecture context; the agent can repeat lookup or misinterpret missing handoff evidence as missing project meaning.

- Components Affected: odylith-context-engine

- Environment(s): Detached source-local maintainer checkpoint c10102f3; native-Claude publication fixture; pre-confirm author and reviewer transport doubles, not model quality qualification.

- Detected By: Unmodified context/bootstrap/session-brief CLI probe plus passive before/after phase trace.

- Failure Signature: Resolved workstream_context contains test-boundary-1 and D-001/D-002 before compact_finalized_bootstrap_payload; delivered workstream_context is absent and context_packet.execution_engine_handshake.target_component_ids is empty.

- Trigger Path: odylith context-engine bootstrap-session --workstream B-001 --intent 'Review the accepted project scope. Do not implement.' on a published source-free project.

- Ownership: Context Engine dossier and bootstrap/session delivery boundary; canonical Execution handshake.

- Timeline: Captured 2026-09-08 through `odylith bug capture`.

- Blast Radius: Published Greenfield and other workstream-only bootstrap/resumption packets; not specific to a host, vocabulary or model.

- SLO/SLA Impact: Avoidable repeated narrowing weakens first-use continuity; no measured Greenfield generation deadline regression is claimed.

- Data Risk: All 96 sealed files and modes, active generation and transaction bytes remain unchanged by the public probes.

- Security/Compliance: Context visibility defect; restoring component identity must not authorize implementation or replay retained instructions.

- Invariant Violated: Canonically resolved evidence selected for a consumer must survive the delivery boundary without downstream semantic reconstruction.

- Root Cause: The bootstrap delivery allowlist omits workstream_context. Its late Execution attachment reads top-level component sources, not the resolved nested dossier. Session packet finalization receives path-impact components and diagrams only; no source paths exist in the accepted project.

- Solution: Dossier compaction now preserves the full typed related_entity_ids map independently of descriptive-row limits. The existing Execution handshake consumes resolved workstream relations and preserves all target IDs. Bootstrap and session brief share the same execution attachment owner and retain their selected dossier. The bootstrap-only path, phrase substitutions, destructive character clipping and duplicate mapping helper are removed. No model call, source rescan, new production module or post-confirm work was added.

- Verification: The original 19 controls produce 16 failures and three passes before repair. The focused suite passes 144 tests after repair; two old phrase-substitution expectations are replaced with complete-source-copy expectations while retaining their target/presentation checks. Frozen broader proof passes 4563 runtime tests in 408.38 seconds and 31 browser integration cases in 165.28 seconds. All 1825 src/tests/config inputs remain unchanged across those runs (SHA-256 411aca6e922d551de5cbf67c0b200896c7961daf5d93b9ccee306c8fa6427c00). Receipts: /private/tmp/odylith-session-handoff-proof.S3jUS4/.

- Public CLI Readback: The separate handoff-after context/bootstrap/resume journey preserves test-boundary-1 and all five diagram IDs. The exact component reaches both the general handshake and execution snapshot. All 96 sealed file bytes/modes, active identity and transaction bytes remain unchanged before/after every command. No retained intent becomes a new instruction and no review-only target becomes writable. Receipts: /private/tmp/odylith-claude-confirmation.5ntA3g/handoff-after-publication-readback.json.

- Explicit Implementation Admission (2026-09-08): Four fresh public session-brief calls over the same published structural fixture distinguish review, input-free review resume, an explicit Python implementation request with two named source/test target paths, and input-free implementation resume. Only the explicit implementation request admits implement.target_scope; it retains B-001 and test-boundary-1. Both resumes preserve saved context without a current instruction and defer implementation. All 96 sealed files/modes, active identity and transaction bytes remain unchanged, and no requested application files are created. The earlier review-only refusal was correct, not a reproduced implementation-admission defect. Calls take 0.886–0.935 seconds; 139 focused seam controls pass. This is source-local admission and custody proof, not native host dispatch, generated-package quality or the complete consumer timing gate. Evidence: /private/tmp/odylith-integrated-handoff.5iSyMI/result.json and seams.xml.

- Tradeoff And Scope: Pretty-printed bootstrap grows from 9390 to 15159 bytes and resume from 7840 to 14220 bytes because selected scope and current execution posture are now delivered. These probes measure snapshot construction at 0.410 and 0.398 milliseconds, not complete generation latency. Descriptive rows remain bounded. The resumed packet still requires narrower execution context; this is not a next-action-admission fix, native intervention qualification, clean-install proof, or semantic-quality/60-90-120 release claim.

- Regression Tests Added: tests/unit/runtime/test_context_relation_handoff.py covers one/five/seven component identities, diagram references, empty/unresolved dossiers, read-only/resumed intent, noncanonical identities beyond display limits, complete prose and instruction-like titles. Two existing bootstrap tests move here from the oversized hardening file; the latter shrinks from 1580 to 1444 lines. Production changes total ten fewer lines across the existing three owners.

- Prevention: Follow CB-029: prove selected evidence reaches the actual consumer before changing retrieval or adding model reasoning.

- Related Incidents/Bugs: CB-029 (selected evidence lost at prompt boundary); CB-332 (distinct retained-session erasure); B-142.

- Code References: - src/odylith/runtime/context_engine/session_bootstrap_payload_compactor.py
- src/odylith/runtime/context_engine/odylith_context_engine_dossier_compaction_runtime.py
- src/odylith/runtime/context_engine/execution_engine_handshake.py
