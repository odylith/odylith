- Bug ID: CB-354

- Status: FixedPendingRelease

- Fixed: Pending

- Fixed In: 0.1.15

- Created: 2026-10-04

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The product-owned Domain Intelligence inventory still advertises pre-confirm repair, atomic record commit and post-confirm surface refresh. Current Greenfield admits one source-verified candidate and publishes an exact sealed package with journaled recovery and no model, semantic repair or projection generation after receipt. The stale inventory misstates the operator contract even though engine-integrity presence checks pass.

- Impact: Operators and host agents receive misleading instructions about supported Greenfield confirmation and publication behavior.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo, v0.1.15 branch, detached source-local maintainer posture, 2026-10-04.

- Detected By: Whole-product capability coverage audit requested by the operator.

- Failure Signature: Domain Intelligence owns pre-confirm repair and activation says commits records atomically and refreshes surfaces.

- Trigger Path: odylith capabilities; Domain Intelligence inventory entry.

- Ownership: Analysis Engine capability_inventory Domain Intelligence descriptor; current transaction ownership remains Domain Intelligence.

- Timeline: Captured 2026-10-04 through `odylith bug capture`.

- Blast Radius: Product-owned CLI capability inventory and consumers that use it for architecture and operation guidance.

- SLO/SLA Impact: No measured runtime latency effect; release contract and operator clarity are affected.

- Data Risk: No governed data mutation demonstrated; incorrect confirmation guarantees are advertised.

- Security/Compliance: No demonstrated security incident; capability text must preserve deterministic authorization and write boundaries.

- Invariant Violated: Product-owned capability inventory must describe the current sealed receipt and commit-only transaction contract.

- Root Cause: Inventory descriptor retained historical mechanism and publication language; existing integrity checks validate presence and anchors rather than these behavioral guarantees.

- Solution: Corrected the existing inventory descriptor to describe source-verified candidate admission, a sealed read-only preview and receipt-bound publication of precompiled bytes under journaled recovery. Names, taxonomy, commands, anchors and runtime topology remain unchanged. The old repair, atomic-commit and post-confirm refresh descriptions are removed.

- Verification: Live capability stdout reports the current read-only preview and journaled commit-only contract. AST comparison against HEAD preserves all 31 inventory identities, categories, command lists and anchors; only the Domain Intelligence descriptions change. Nine existing engine-integrity and host-contract checks pass. Evidence: /private/tmp/odylith-greenfield-capability-inventory-proof-20261004.json. This verifies the metadata correction, not consumer semantic quality or release readiness.

- Agent Guardrails: Use current owned runtime/spec law over historical inventory prose; never infer publication guarantees from passing inventory presence checks.

- Related Incidents/Bugs: CB-324

- Code References: - src/odylith/runtime/analysis_engine/capability_inventory.py
- tests/unit/runtime/test_engine_integrity.py
