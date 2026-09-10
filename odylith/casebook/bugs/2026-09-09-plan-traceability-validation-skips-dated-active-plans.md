- Bug ID: CB-334

- Frozen Checkpoint Verification (2026-09-09): The final frozen source passes 5,002 runtime, 1,168 install and 340 browser checks (one fixture skip), plus ten current-record desktop/mobile checks and three root CLI checks. All 3,191 selected proof inputs remain identical. The actual governance gate validates 25 active reference plans and 95 risk plans; zero-coverage success is no longer accepted. This is the integrated source checkpoint, not release qualification.

- Reporting Proof (2026-09-09): Four risk-validator missing/empty/count controls fail before correction and pass afterward. Both validators now report their actual selected inventory; the live CLI reports 25 active traceability plans and 95 active/completed risk plans. Existing empty scopes are explicitly not applicable and absent required scopes fail. Combined focused proof has 84 passes; wider regression and generated readback remain pending.

- Adjacent Empty-scope Finding (2026-09-09): The risk/mitigation validator still prints `contract passed` for an existing empty active/completed plan scope. A maintained CLI test reproduces this failure (`risk-empty-red.xml`); traceability's corrected reporting does not cover this separate entrypoint. Select one plan inventory for validation and reporting, print its count on failure or success, and label an existing empty scope not applicable. Missing required plan directories must not earn a passing result. Keep the normalizer's write contract and checked-file set aligned rather than counting a second filesystem scan.

- Current Gate (2026-09-09): The current CLI passes all 25 active plans after source-backed reference sections and two scoped operational runbooks are added. Both dot-path stripping operations are removed. This replaces the earlier all-25 missing-reference failure below without restoring retired owners or weakening path/bucket checks. Wider regression proof and CB-335 formatter correction remain pending; the traceability result is not whole-release acceptance.

- Current-reference Finding (2026-09-09): The 25-plan reference audit supplies grounded operational, developer-document, and current-code links. The real gate identified a false failure on the existing `.github/workflows/release.yml`: both initial punctuation stripping and final `lstrip("./")` destroy path identity. Removing only the latter does not fix the failure. Preserve the exact Markdown-delimited path token and use Path's own relative-path normalization; hidden-directory and ordinary `./` controls reproduce all three failures. This is a source-reference identity correction, not permission to waive missing paths or restore retired owners.

- Coverage Proof (2026-09-09): The focused before-change run has nine genuine missed-coverage/reporting failures, one expected new-call-signature control failure, and six passes. After the correction, all 18 traceability/risk controls pass, with five CLI dispatch checks also passing. The real traceability CLI now checks 25 plans and fails all 25 for missing required Traceability sections. The risk check identifies ten candidate rewrites; a read-only diff shows seven would invent placeholder risks or mitigations from already complete wrapped list items. No normalization write ran. These newly visible findings are not waived and the broader governance gate remains failed.

- Bounded Correction Scope (2026-09-09): Native CLI and sync call the traceability module entrypoint; there are no direct production callers of its Python validation function. Select existing active Markdown files recursively once, pass that inventory into validation, and report its count on success or failure. An existing empty active directory is not applicable, while a missing required directory remains an error. The adjacent risk normalizer also selects only direct-child active plans; correct that same omission without changing Markdown interpretation or completed-plan coverage. Add dated positive/negative and empty-scope controls before changing production code. No reusable plan-discovery owner covers this exact filesystem contract; use the existing path primitive instead of adding another abstraction.

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
