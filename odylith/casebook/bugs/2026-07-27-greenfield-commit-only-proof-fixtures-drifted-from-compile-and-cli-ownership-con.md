- Bug ID: CB-294

- Status: Open

- Created: 2026-07-27

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: Two contract tests no longer represent a valid Greenfield flow. One marks a proposal compile-ready while omitting required diagram project-intelligence bindings, so pre-confirm compilation correctly rejects it. Another assumes the proposal CLI module directly owns commit execution even though create now dispatches to the dedicated commit owner. Together they leave the end-to-end commit-only proof red despite the intended product boundary being correct.

- Impact: Blocks credible proof that a valid sealed transaction can proceed through the command surface without post-confirm semantic work.

- Components Affected: greenfield-governance

- Environment(s): Product-repo maintainer source-local proof

- Detected By: Independent adversarial review

- Failure Signature: Compile-ready transaction fixture fails pre-confirm tribunal for missing diagram project-intelligence bindings; ownership guard fails after create CLI dispatch split.

- Trigger Path: Focused Greenfield commit-only boundary and proposal ownership tests

- Ownership: Greenfield test fixtures and CLI ownership guard

- Timeline: Captured 2026-07-27 through `odylith bug capture`.

- Blast Radius: Commit-only proof, architecture guard, and release confidence for Greenfield.

- SLO/SLA Impact: Prevents release-quality verification from completing.

- Data Risk: No governed data loss; the defects are test-contract drift caught before release.

- Security/Compliance: Policy, privacy, accessibility, and safety assessment: no control bypass; stale tests could mask a transaction-integrity regression if left unresolved.

- Invariant Violated: Compile-ready inputs must satisfy all current pre-confirm contracts, and the CLI ownership guard must reflect the single commit owner.

- Root Cause: Fixtures and architecture assertions were not migrated when diagram bindings became required and create dispatch moved to a dedicated owner.

- Solution: Bring the fixture to the current compiled diagram contract and assert a single dispatch boundary rather than direct execution from the proposal CLI.

- Rollback/Forward Fix: No rollback required; update tests to model the current fail-closed contract.

- Verification: Focused boundary and ownership tests pass, then installed release matrix exercises the valid precompiled commit flow.

- Prevention: When compiler contracts or command ownership move, update their commit-only fixtures and structural guards in the same change.

- Agent Guardrails: Do not remove the diagram binding requirement or fold commit execution back into the proposal CLI merely to satisfy old tests.

- Code References: - tests/unit/runtime/test_greenfield_apply_commit_only_boundary.py
- tests/unit/runtime/test_greenfield_proposals.py
- src/odylith/runtime/domain_intelligence/greenfield_proposals_cli.py
- src/odylith/runtime/domain_intelligence/greenfield_create_cli.py
