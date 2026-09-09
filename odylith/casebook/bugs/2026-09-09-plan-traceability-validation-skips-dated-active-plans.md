- Bug ID: CB-334

- Status: Open

- Created: 2026-09-09

- Severity: P2

- Reproducibility: Always

- Type: Tooling

- Description: The sync gate reports plan traceability passed with plans validated: 0, while the supported in-progress tree contains 25 dated plan files, including B-142. The validator's direct-child glob skips them all. This is an existing coverage defect at ca1ed52c, not a regression in the completion-aware wait correction.

- Impact: Maintainers can mistake a zero-coverage traceability gate for evidence that active plans have valid runbook, developer-document and code references.

- Components Affected: odylith

- Environment(s): Odylith product-repo detached source-local proof checkout on 2026-09-09, with date-partitioned active plan directories.

- Detected By: Maintainer audit of the successful sync transcript against the physical active-plan inventory and validator implementation.

- Failure Signature: The traceability gate prints plans validated: 0 although 25 in-progress Markdown plans exist beneath YYYY-MM directories.

- Trigger Path: odylith validate plan-traceability --repo-root .; the same owner runs inside odylith sync.

- Ownership: Odylith governance plan discovery and traceability validation.

- Timeline: Captured 2026-09-09 through `odylith bug capture`.

- Blast Radius: Date-partitioned active technical plans and the sync or release gates consuming this validator.

- SLO/SLA Impact: Release-proof coverage is unproven; no direct consumer latency regression is demonstrated.

- Data Risk: No observed data loss or publication; invalid plan references can remain undetected.

- Security/Compliance: No demonstrated exploit or credential impact; audit assurance is incomplete.

- Invariant Violated: A required zero-of-zero validation must not be reported as passed; the validator must cover the supported active-plan layout.

- Root Cause: Both validation and reporting use in-progress glob('*.md') rather than the supported nested active-plan inventory.

- Solution: Use one authoritative active-plan selection for validation and counts, cover dated subdirectories, and report an actually empty scope explicitly as not applicable.

- Verification: Add valid and invalid dated-plan controls plus empty-scope coverage; validate the current active-plan inventory without waiving discovered stale references.

- Agent Guardrails: Do not infer governance closure from exit code zero or aggregate unit counts when the owning validator checked no required records.

- Version/Build: Existing validator is unchanged from ca1ed52c8328f436f2aac4762374a1aa1ea1a11d.

- Related Incidents/Bugs: CB-303; B-142 release and governance proof.

- Code References: - src/odylith/runtime/governance/validate_plan_traceability_contract.py
