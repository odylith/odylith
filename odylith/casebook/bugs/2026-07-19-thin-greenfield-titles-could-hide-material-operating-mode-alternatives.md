- Bug ID: CB-288

- Status: Open

- Created: 2026-07-19

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Title-supported first-path inference recognized only a narrow ambiguity pattern. A thin request that explicitly contrasted mutually exclusive operating modes could compile a guessed path and present it as an assumption instead of asking one focused pre-confirm question.

- Impact: Users could confirm a product interpretation that chose a material first-release operating mode without an explicit decision.

- Components Affected: domain-intelligence

- Environment(s): Thin or title-led Greenfield proposals.

- Detected By: Independent consumer UX and materiality review

- Failure Signature: title_supports_conservative_first_path returned true for title-only evidence containing manual or automated batch release.

- Trigger Path: greenfield propose with a domain-anchored title and explicit operating-mode alternatives.

- Ownership: Greenfield prompt materiality gate

- Timeline: Captured 2026-07-19 through `odylith bug capture`.

- Blast Radius: Thin prompts where mutually exclusive modes alter the first complete path.

- SLO/SLA Impact: Material clarification contract was not reliably enforced before confirmation.

- Data Risk: No post-confirm partial write risk; accepted product scope could be wrong.

- Security/Compliance: Security: no direct exposure. Privacy: no changed data handling. Accessibility: one focused clarification improves command comprehension. Compliance: material review or approval mode must not be silently inferred.

- Invariant Violated: Ambiguity that changes the first complete path must trigger a focused pre-confirm clarification, not a hidden assumption.

- Root Cause: The title inference heuristic lacked explicit operating-mode alternative detection.

- Solution: Treat connector-based alternatives between mutually exclusive generic operating modes as material during title-only inference while retaining ordinary default assumptions.

- Rollback/Forward Fix: Forward fix; existing unconfirmed proposals rebuild from evidence.

- Verification: Materiality unit tests cover manual or automated, live or fixture, self-service or staff-review, and an ordinary-assumption control.

- Prevention: Add materiality variants to the installed chaos corpus and reject any title-inference path that collapses explicit operating alternatives.

- Agent Guardrails: Do not return Product Intent failures for thin evidence; ask one useful question only when an explicit alternative changes release truth.

- Preflight Checks: Run prompt materiality and Greenfield CLI clarification-path tests before release.

- Regression Tests Added: test_title_only_operating_mode_alternatives_require_clarification

- Monitoring Updates: Intent chaos telemetry should record materiality classifications and clarification outcomes.

- Version/Build: 0.1.15 candidate

- Config/Flags: Default proposal path

- Customer Comms: Caught before release; no customer communication needed.

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materiality.py
