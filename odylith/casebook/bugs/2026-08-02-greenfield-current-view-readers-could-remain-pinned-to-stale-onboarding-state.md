- Bug ID: CB-305

- Status: Open

- Created: 2026-08-02

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: After a Greenfield generation became active, later governed writers changed the live managed tree without a shared completion signal. The post-confirm reader could keep presenting the immutable onboarding generation as current, while naive drift routing could expose an in-progress or failed partial writer.

- Impact: Users could be sent to stale governance state after successful later writes, or to uncertain partial live bytes if drift were handled without writer coordination.

- Components Affected: domain-intelligence

- Environment(s): Odylith 0.1.15 maintainer source and installed Greenfield contract

- Detected By: Adversarial transaction and recovery review under B-142

- Failure Signature: Active generation remains status=active after a later managed-path mutation; no production supersession caller distinguishes successful, failed, and in-flight writers.

- Trigger Path: Greenfield CONFIRM followed by any supported Odylith CLI command that mutates GREENFIELD_REPOSITORY_WRITE_PATHS

- Ownership: Domain Intelligence Greenfield transaction and canonical handoff boundary

- Timeline: Captured 2026-08-02 through `odylith bug capture`.

- Blast Radius: All Greenfield repositories that receive later Radar, Registry, Atlas, Compass, Casebook, shell, or bundle mutations

- SLO/SLA Impact: Blocks release claim for package-level canonical visibility

- Data Risk: No sealed bytes are lost; stale or partial governance visibility can misdirect subsequent work.

- Security/Compliance: No direct security escalation; integrity and auditability boundary violated.

- Invariant Violated: Canonical readers must resolve a coherent active generation and move to live truth only after a successful changed writer completes.

- Root Cause: The active-generation pointer had no cooperating later-writer boundary; supersession existed only as an unused primitive and reader drift alone could not distinguish success from partial failure.

- Solution: Serialize supported CLI mutations with the Greenfield repository lock, retain the old generation while a writer runs, supersede only after zero-exit changed managed readback, fail closed on unexplained drift, and retain exact reviewed-generation routes.

- Rollback/Forward Fix: Forward fix; preserve immutable generations and existing journals.

- Verification: 84 focused atomic/custody tests pass, including in-flight reader, changed success, failed partial, no-op, exact receipt, and lock contention cases; real CLI contract tests cover immutable navigation.

- Prevention: Keep command_may_mutate_greenfield_managed_paths conservative, require run_with_greenfield_managed_mutation_boundary around top-level CLI dispatch, and block merges unless test_greenfield_managed_mutation_boundary.py proves changed-success, failed, no-op, and contention behavior.

- Agent Guardrails: Never route live on fingerprint drift without a durable writer completion signal; never supersede before successful changed readback.

- Preflight Checks: Run the managed mutation boundary tests, generation/journal tests, host confirmation tests, and Atlas D-043 freshness check.

- Regression Tests Added: tests/unit/runtime/test_greenfield_managed_mutation_boundary.py

- Related Incidents/Bugs: CB-304; B-142

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_managed_mutation_boundary.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_handoff.py
- tests/unit/runtime/test_greenfield_managed_mutation_boundary.py
