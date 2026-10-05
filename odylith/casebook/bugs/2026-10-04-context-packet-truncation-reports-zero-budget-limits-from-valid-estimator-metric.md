- Bug ID: CB-356

- Status: FixedPendingRelease

## Verified correction (2026-10-04)

Two finalization reads now use the estimator's actual budget_bytes/budget_tokens
keys. The existing characterization test uses the real estimator rather than
fabricated metrics: it fails before the correction; the finalization test file
and aggregate bootstrap control pass 19 tests. Independent supplemental proof
passes both required boundary/aggregate controls with accurate 24,000-byte and
6,000-token limits, preserves retry metadata and retains admitted evidence.
Actual cap enforcement and allocation are unchanged.

Receipt: /private/tmp/odylith-context-packet-budget-telemetry-green-receipt-20261004.json,
SHA-256 5d40fe30952f8645a99e9f824a6feb08ffde114a21022368530e2610afc7b7e2.
Independent proof:
/private/tmp/odylith-history-memory-h1-independent-telemetry-final-20261004.md,
SHA-256 0450f67e329dd311e5478aea19c9f791b19b7c647d5ee1a7b287178d6ab33d05.
No actionable P0/P1/P2 remains in the bounded H1 slice; complete frozen
runtime/install validation and release remain open.

- Created: 2026-10-04

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The actual packet estimator emits budget_bytes and budget_tokens, while final truncation sync reads nonexistent max_bytes and max_tokens. Actual cap enforcement remains correct, but emitted truncation metadata reports zero limits. An existing unit fixture fabricates the wrong estimator shape and masks the integration failure. Independent H1 aggregate packet proof exposes the mismatch.

- Impact: Packet telemetry becomes misleading and prevents operators from trusting emitted budget and efficiency evidence.

- Components Affected: odylith-context-engine

- Environment(s): Product repo detached source-local maintainer posture on existing v0.1.15 branch.

- Detected By: Independent H1 aggregate packet review and maintainer actual-estimator control

- Failure Signature: Estimator budget_bytes=1024 and budget_tokens=256 becomes truncation.packet_budget.max_bytes=0 and max_tokens=0.

- Trigger Path: tooling_context_budgeting.estimate_packet_metrics -> tooling_context_packet_finalization.sync_packet_budget_truncation

- Ownership: Context Engine packet budgeting and finalization contract

- Timeline: Captured 2026-10-04 through `odylith bug capture`.

- Blast Radius: Codex and Claude compact Context Engine packet budget telemetry.

- SLO/SLA Impact: No cap or measured latency breach; reported budget limits are incorrect.

- Data Risk: No source loss or private data leak demonstrated.

- Security/Compliance: No security or compliance incident demonstrated.

- Invariant Violated: Final emitted budget limits must retain the actual estimator allocation and cannot fabricate zero values.

- Root Cause: Finalization reads max_bytes/max_tokens from estimator metrics whose canonical keys are budget_bytes/budget_tokens.

- Solution: Adopt the actual estimator keys in the existing finalization owner and characterize the real producer-to-consumer boundary.

- Verification: Retain /private/tmp/odylith-context-packet-budget-telemetry-red-20261004.json SHA256 a6cd20cc0c7e32b068754e6bb1e50aa2340f391910bad227a2ca2e7817dad448; require real estimator/truncation round-trip and aggregate H1 packet proof.

- Prevention: Tests must use actual estimator output rather than a fabricated incompatible metrics dictionary.

- Related Incidents/Bugs: CB-355, B-133 H1, B-142 complete frozen packet regression

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/context_engine/tooling_context_packet_finalization.py
- src/odylith/runtime/context_engine/tooling_context_budgeting.py
- tests/unit/runtime/test_tooling_context_packet_builder.py
