- Bug ID: CB-342

- Status: Open

- Created: 2026-09-23

- Severity: P2

- Reproducibility: Consistent

- Type: Product

- Description: build_coding_readiness_contract uses a deduplicating helper for evidence_requirements, operational_constraints, and non_goals even though the contract declares preserve_exact_source_facts. Two identical source citations collapse into one in the coding-readiness contract and renderer, losing source multiplicity while project handoff scope preserves it.

- Impact: Operators receive a coding-readiness handoff that cannot distinguish repeated source citations or repeated constraints, weakening exact semantic custody and downstream review.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo; typed Greenfield proposal handoff, source-local runtime

- Detected By: Read-only typed-authorship audit and focused contract inspection after 2,065 non-holdout Greenfield tests

- Failure Signature: build_coding_readiness_contract(evidence_requirements=(x,x)) returns (x,) and render_coding_readiness_gates omits the repeated fact

- Trigger Path: greenfield proposal to coding-readiness handoff projection

- Ownership: Greenfield handoff contract owner

- Timeline: Captured 2026-09-23 through `odylith bug capture`.

- Blast Radius: Coding-readiness previews and handoff artifacts for proposals with repeated source facts

- SLO/SLA Impact: No transaction safety failure; semantic fidelity defect in a release-readiness surface

- Data Risk: Source evidence is not mutated, but multiplicity is lost in projection

- Security/Compliance: No direct security exposure; governance trust and source-custody risk

- Invariant Violated: Structural projections must preserve exact accepted source facts and must not deduplicate source meaning unless explicitly authorized

- Workaround: Use the project handoff scope contract, which already preserves repeated source bytes; do not claim coding-readiness exact custody until fixed

- Root Cause: _exact_strings deduplicates by value and is reused by the coding-readiness builder and renderer despite the coding-readiness gate policy requiring exact source facts

- Solution: Add a source-fact copy helper that preserves order, whitespace, and repeated non-empty values; use it only for coding-readiness source-fact fields and renderer, leaving normalized/deduplicated command/reference helpers unchanged

- Rollback/Forward Fix: Forward-fix the handoff contract with one focused regression test; revert only the helper call sites if unrelated consumers regress

- Verification: Regression test with duplicate evidence, constraint, and non-goal values; focused handoff suite; full non-holdout Greenfield suite; independent semantic review

- Prevention: Keep exact source-fact copy separate from normalized or deduplicated command/reference helpers and test duplicate, Unicode, whitespace, and empty-input cases

- Agent Guardrails: Do not add regex, vocabulary, parser, model repair, or broad schema changes; preserve typed source custody

- Preflight Checks: Search Casebook and current handoff tests; confirm project handoff already preserves repeated source bytes; keep final holdout untouched

- Regression Tests Added: Existing test_greenfield_handoff_contract.py proves repeated project-handoff bytes and exact Unicode/whitespace; add the coding-readiness duplicate regression in the forward fix before closure

- Version/Build: 0.1.15 source-local detached posture; branch 2026/freedom/pending-work-checkpoint-20260906 at 61bf8409

- Related Incidents/Bugs: 2026-08-02-greenfield-project-surfaces-repeated-and-clipped-canonical-meaning
