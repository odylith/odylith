- Bug ID: CB-295

- Status: Open

- Created: 2026-07-27

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: The deterministic semantic-completion stage can append Atlas diagram rows after proposal normalization attached project-intelligence bindings. The pre-confirm tribunal then rejects an otherwise compilable proposal because those late rows lack required provenance.

- Impact: A valid host-reasoned Greenfield proposal can fail before confirmation with an internal binding-contract error instead of reaching the reviewed confirmation view.

- Components Affected: greenfield-preconfirm-compiler

- Environment(s): Odylith product-repo maintainer source-local test posture

- Detected By: Focused Greenfield proposal regression

- Failure Signature: diagram row 3/4/5/6 must carry project_intelligence_binding

- Trigger Path: normalize host-reasoned proposal -> deterministic semantic completion -> compile -> pre-confirm tribunal

- Ownership: Greenfield pre-confirm compiler

- Timeline: Observed while running the full proposal suite after strict authority-binding and fixture repairs; the tribunal correctly rejected late-generated unbound diagram rows.

- Blast Radius: Host-reasoned Greenfield proposals whose semantic completion adds Atlas diagrams

- SLO/SLA Impact: Blocks proposal readiness and delays a deterministic confirmation contract

- Data Risk: No governed write occurs; tribunal fails closed before transaction sealing

- Security/Compliance: Provenance and audit policy requires each final generated diagram row to identify its supporting project intelligence; the missing binding prevents compliance-grade traceability.

- Invariant Violated: Every final diagram row must have a project-intelligence binding before tribunal validation and transaction sealing

- Workaround: Rebuild through a path that re-normalizes the final diagrams before tribunal; do not bypass the tribunal.

- Root Cause: Bindings were attached before semantic completion, but semantic completion could add new rows without rebinding the final projection.

- Solution: Reattach project-intelligence bindings after the final semantic projection step, before tribunal evaluation and authority sealing.

- Rollback/Forward Fix: No rollback required because pre-confirm failure prevents governed writes; forward-fix the compiler ordering and retain fail-closed tribunal behavior.

- Verification: Run the scalar-wave proposal regression and the complete Greenfield proposal, transaction, custody, browser, and installed-release matrices.

- Prevention: Keep bindings as a final deterministic compiler projection and cover late-generated diagram rows with a regression.

- Agent Guardrails: Do not repair or bind governed artifacts after CONFIRM; all final projections must be complete before the transaction is sealed.

- Preflight Checks: Assert every final diagram row has a project-intelligence binding before tribunal invocation.

- Regression Tests Added: Scalar-wave proposal regression covers deterministic diagrams added during semantic completion.

- Monitoring Updates: Casebook record tracks the compiler-ordering defect until final matrix proof is complete.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_preconfirm_patch_apply.py
- tests/unit/runtime/test_greenfield_proposals.py
