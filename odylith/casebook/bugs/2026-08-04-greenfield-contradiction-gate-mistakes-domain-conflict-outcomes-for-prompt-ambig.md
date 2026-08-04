- Bug ID: CB-319

- Status: FixedPendingRelease

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A complete reservation workflow containing 'record either a conflict or an accepted reservation' is diverted to clarification because the explicit contradiction regex treats any occurrence of conflict as contradictory user evidence.

- Impact: Product completion risk: users with valid workflows involving conflict states cannot reach a creation-ready proposal and receive an irrelevant clarification question.

- Components Affected: domain-intelligence

- Environment(s): Odylith product-repo source-local Greenfield CLI suite

- Detected By: Full Greenfield CLI path regression suite

- Failure Signature: test_greenfield_cli_compiles_a_complete_reservation_path_without_temp_path_leaks returned clarification_required instead of product_create_transaction

- Trigger Path: odylith greenfield propose with a complete workflow whose domain outcome contains the noun conflict

- Ownership: Greenfield materiality gate and prompt evidence interpretation

- Timeline: Captured 2026-08-04 through `odylith bug capture`.

- Blast Radius: Any domain that records, resolves, displays, or routes conflict states

- SLO/SLA Impact: Operational completion SLO blocked before confirmation for otherwise complete prompts

- Data Risk: Data risk is limited because no governed writes occur; the failure is a false clarification

- Security/Compliance: Security posture has no direct change; compliance and safety policy remain pre-confirm because no write occurs

- Invariant Violated: Domain vocabulary must not be treated as meta-level contradictory evidence without explicit disagreement framing

- Root Cause: _EXPLICIT_CONTRADICTION_RE matched bare conflict vocabulary without requiring evidence or requirement disagreement context

- Solution: Require explicit disagreement framing around conflict or contradiction terms and retain field-specific contradiction cases

- Rollback/Forward Fix: Forward fix the materiality predicate and add domain-conflict regression coverage

- Verification: The focused materiality and exact reservation compile pack passes 19/19. The complete 60-case Greenfield CLI path suite remains the release checkpoint.

- Prevention: Keep domain outcome terms separate from evidence-relation predicates

- Agent Guardrails: Do not classify semantic ambiguity from isolated overloaded nouns; require relation-level evidence

- Preflight Checks: Exercise valid product flows containing conflict, contradiction, unresolved, public, and private as domain data

- Regression Tests Added: `test_domain_conflict_outcome_does_not_invent_a_material_contradiction` proves the complete reservation path compiles; the existing audience and proof-boundary disagreement cases still ask one focused question.

- Version/Build: 2026/freedom/v0.1.15 at e00f3addb

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_material_clarification.py
- tests/unit/runtime/test_greenfield_final_holdout_regressions.py
