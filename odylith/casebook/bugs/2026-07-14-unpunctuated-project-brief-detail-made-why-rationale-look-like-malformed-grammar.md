- Bug ID: CB-247

- Status: Open

- Created: 2026-07-14

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A normal thin prompt produced an unpunctuated first-path detail followed by inline Why rationale. The renderer merged them into one line, so the pre-confirm quality gate read the rationale conjunction as coordinated modal drift and withheld CONFIRM.

- Impact: Ordinary consumer prompts can be denied a ready transaction for a renderer-owned grammar issue instead of receiving an internal repair.

- Components Affected: domain-intelligence

- Environment(s): fresh installed 0.1.15 candidate wheel on macOS temporary consumer repo

- Detected By: fresh installed thin-prompt propose smoke

- Failure Signature: Project brief project-brief.v1.md has coordinated modal grammar drift near and prevents

- Trigger Path: odylith greenfield propose with a municipal permit-review workspace prompt

- Ownership: Greenfield Project Brief renderer and pre-confirm package quality

- Timeline: Captured 2026-07-14 through `odylith bug capture`.

- Blast Radius: Any blueprint detail without terminal punctuation followed by inline Why rationale

- SLO/SLA Impact: Blocks transaction readiness before confirmation and adds avoidable user friction.

- Data Risk: No governed writes occur before the failure; risk is consumer utility and delivery latency.

- Security/Compliance: Privacy, accessibility, safety, policy, and compliance posture: no direct impact; quality gates must remain strict and internal repairable.

- Invariant Violated: Non-material renderer defects must be repaired before confirmation rather than surfaced as a Product Intent failure.

- Root Cause: The Project Brief renderer appended Why on the same line even when must_capture was a clause rather than a complete sentence.

- Solution: Render Why as an indented bullet whenever the detail lacks terminal sentence punctuation, preserving the strict grammar gate.

- Rollback/Forward Fix: Forward fix only; no consumer governance migration.

- Verification: Focused Project Brief and prewrite suite: 80 passed in 23m46s. Exact thin source replay compiled a passed transaction and confirmed create committed 4 workstreams, 3 component specs, and 6 Atlas diagrams.

- Prevention: Keep rationale layout sentence-aware; do not weaken the coordinated-modal detector or add domain-specific phrase exceptions.

- Agent Guardrails: Treat renderer-owned punctuation and layout defects as internal pre-confirm repair work, never as a consumer clarification.

- Regression Tests Added: test_project_brief_rendering_separates_rationale_after_unpunctuated_detail

- Version/Build: 0.1.15 candidate

- Related Incidents/Bugs: CB-210

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_project_brief.py
