- Bug ID: CB-332

- Status: FixedPendingRelease

- Created: 2026-09-08

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A published Greenfield project resolves through exact context lookup. Bootstrap stores its selected workstream and read-only intent. A subsequent session-brief call with only the same session ID returns no workstream and overwrites both stored workstream and intent with empty strings. The two calls run within the active lease; the immutable package remains byte-for-byte unchanged.

- Impact: A resumed operator loses the selected project workstream and prior constraints, must restate known context, and cannot rely on the memory-to-execution handoff.

- Components Affected: odylith-context-engine

- Environment(s): Detached source-local maintainer proof at bd3a7340, exercising the public CLI against a real native-Claude-published structural fixture.

- Detected By: Two consecutive public CLI integration probes with persisted session records captured before and after the second call.

- Failure Signature: bootstrap-session with workstream and read-only intent persists both values; session-brief with the same session ID alone persists empty workstream and intent.

- Trigger Path: odylith context-engine bootstrap-session --session-id S --workstream B-001 --intent read-only review, followed by odylith context-engine session-brief --session-id S.

- Ownership: Context Engine session packet assembly and session-state persistence.

- Timeline: Captured 2026-09-08 through `odylith bug capture`.

- Blast Radius: Session-aware Greenfield completion handoffs and ordinary workstream-first resumption; exact-ref lookup still succeeds.

- SLO/SLA Impact: Repeated narrowing and loss of already-supplied constraints reduce consumer utility; this is not measured Greenfield generation latency.

- Data Risk: The persisted session context is overwritten. Independent comparison verifies all 96 sealed project files and modes, publication identity and transaction bytes remain unchanged.

- Security/Compliance: No unauthorized mutation observed. Retained context is evidence, not permission; recovery must not promote queued work or override a new user instruction.

- Invariant Violated: A session read without replacement input must preserve recoverable selected context and constraints rather than erase them.

- Root Cause: build_session_brief selects from current path and workstream arguments without recovering the stored workstream or intent. register_session_state then replaces the session record with the empty selection and intent.

- Solution: Full-profile input-free session reads now recover a live saved workstream through a fresh canonical lookup. The extracted session_workstream_selection phase owns explicit, impact-derived and retained selection; the packet builder no longer duplicates it. Retained selection is identified as context, not an explicit override. The saved intent remains in the session record and visible compact session summary, but never becomes current turn intent, impact input or a replayed execution instruction. New scope input, expired/missing sessions and missing canonical anchors do not inherit prior instructions. Agent hot-path behavior is unchanged.

- Verification: Two positive regression cases fail before the repair while 19 negative/hot-path controls pass. After the repair, all 23 resumption controls and the broader focused context selection pass: 96 tests in 3.60 seconds. The public CLI probe at /private/tmp/odylith-claude-confirmation.5ntA3g/persistence-after-publication-readback.json retains B-001 and the read-only intent, resolves the linked component and diagrams, and independently preserves all 96 sealed file bytes/modes plus publication identity and transaction hash. The before probe is retained separately. The frozen full runtime suite passes 4544 tests in 360.39 seconds, excluding the protected holdout before collection. Targeted cross-surface normal/empty/error, navigation and killed-publication browser checks pass 31 tests in 149.86 seconds. Both JUnit receipts are under /private/tmp/odylith-session-resume-proof.45l4zG/. The 3162-file pre/post-run fingerprint is unchanged: fc60fe82d1dc4059cb22e44130d12552b8bfea8d8ea775dff9d9e366c1e21c7d. This is source-local structural integration evidence, not live generated-package quality, latency qualification, installed release proof or complete execution routing.

- Decision: Reject a blind merge or replay of stored intent into current turn inputs: either could carry stale scope or reissue an earlier implementation request. Use only an input-free, lease-valid, canonically revalidated context read. Positive read/implementation-intent controls plus replacement, expiry, projection loss, compaction, phase ownership and hot-path controls make that boundary falsifiable.

- Agent Guardrails: Do not infer memory success from status counters, parse prose into authority, add vocabulary rules, or treat remembered workstream selection as permission to implement.

- Version/Build: 0.1.15 development; bd3a7340

- Code References: - src/odylith/runtime/context_engine/odylith_context_engine_packet_session_runtime.py
- src/odylith/runtime/context_engine/odylith_context_engine_hot_path_scope_runtime.py
- src/odylith/runtime/context_engine/session_workstream_selection.py
- tests/unit/runtime/test_context_session_resumption.py

- Runbook References: - odylith/technical-plans/in-progress/2026-06/2026-06-26-greenfield-typed-semantic-compiler-and-patchset-repair.md
