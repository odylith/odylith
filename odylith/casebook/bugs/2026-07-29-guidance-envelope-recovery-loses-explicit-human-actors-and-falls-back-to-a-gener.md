- Bug ID: CB-296

- Status: Open

- Created: 2026-07-29

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: When a normal prompt is wrapped in the Greenfield guidance envelope, actor clauses such as experimental physicists, a homeowner, teachers, students, and lab coordinators can be missed. The typed intent then invents a generic workspace user and degrades the accepted first path.

- Impact: Users receive a lower-fidelity proposal despite supplying explicit human roles and workflow actions.

- Components Affected: greenfield-prompt-intent-materialization

- Environment(s): Product-repo source-local verification

- Detected By: Confirmed-intent recovery and high-variance regression suite

- Failure Signature: human_actors falls back to '<workspace> User' or retains only a trailing actor clause

- Trigger Path: guidance envelope -> parse_confirmed_intent_text -> typed Product Intent materialization

- Ownership: Greenfield typed-intent compiler

- Timeline: Found in the fresh custody and variance suite after the staged-write proof passed.

- Blast Radius: Normal thin and detailed prompts with for-who, where, and coordinated actor clauses

- SLO/SLA Impact: Proposal fidelity fails before confirmation and can cause unnecessary user edits

- Data Risk: No governed write occurs because the defect is visible before sealing

- Security/Compliance: The typed-intent boundary must retain supplied actor roles so safety and proof ownership are not silently reassigned to an invented generic user.

- Invariant Violated: Explicit human actors and their actions must survive evidence intake into typed Product Intent without generic persona fallback.

- Workaround: Use a sectioned confirmation that explicitly names Human actors; do not rely on the fallback.

- Root Cause: Prompt-source actor extraction does not consistently traverse the guidance envelope and coordinated actor clauses before title-based fallback.

- Solution: Repair deterministic actor extraction and prioritization at the typed-intent materialization boundary; preserve the supplied roles and scoped actions before authority sealing.

- Rollback/Forward Fix: No rollback needed because the defect is pre-confirm; forward-fix the parser and retain fail-closed materiality behavior.

- Verification: Run the four focused recovery regressions, then the full high-variance and custody suite, CLI/source parity, and installed matrix.

- Prevention: Keep actor clause extraction independent of host wording and cover for-who, where, singular, and coordinated plural forms.

- Agent Guardrails: Never replace an explicit human role with a generic workspace user merely because the input is guidance-wrapped.

- Preflight Checks: Assert parsed human actor labels derive from supplied evidence before confirming a package.

- Regression Tests Added: Existing confirmed-intent recovery regressions cover all reported forms.

- Monitoring Updates: Casebook record tracks the parser regression until release proof is complete.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_prompt_source.py
- tests/unit/runtime/test_greenfield_confirmed_intent_recovery.py
