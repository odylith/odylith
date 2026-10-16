- Bug ID: CB-254

- Status: Open

- Created: 2026-07-16

- Severity: P2

- Reproducibility: Always

- Type: OperatorUX

- Description: The installed Greenfield clarification matrix passed its no-write contract, but the human summary iterated a string score explanation and emitted one character per score line.

- Impact: Release-proof operators receive unreadable clarification verdict output and can miss the actual no-write result.

- Components Affected: odylith

- Environment(s): Local installed release matrix, version 0.1.15.

- Detected By: Installed CAR-T clarification contract proof.

- Failure Signature: score: c followed by one character per line instead of one complete clarification verdict.

- Trigger Path: bin/greenfield-preconfirm-matrix with a clarification_required case and human summary output.

- Ownership: Greenfield release matrix reporting.

- Timeline: Captured 2026-07-16 through `odylith bug capture`.

- Blast Radius: All matrix runs containing clarification_required cases.

- SLO/SLA Impact: No product write or release correctness impact; operator proof readability is degraded.

- Data Risk: None; summary-only failure.

- Security/Compliance: No security or compliance impact.

- Invariant Violated: Human-visible release proof must render complete, grammatical summary lines.

- Root Cause: clarification_quality_verdict supplied a string where GreenfieldQualityVerdict requires a tuple of explanation lines.

- Solution: Wrap the clarification explanation in a one-element tuple at the typed verdict boundary.

- Rollback/Forward Fix: Forward fix only; no governed product records require repair.

- Verification: Run the clarification matrix tests and an installed CAR-T clarification shard; require one complete score line.

- Prevention: Preserve the typed tuple contract with a dedicated clarification verdict regression test.

- Agent Guardrails: Treat character-per-line generated output as AI slop and repair it at the typed source boundary.

- Preflight Checks: Inspect human matrix output for clarification_required cases.

- Regression Tests Added: tests/unit/install/test_greenfield_matrix_clarification.py

- Monitoring Updates: Installed proof shard now covers the clarification summary path.

- Version/Build: 0.1.15 source checkpoint 71955bb39.

- Config/Flags: RESCUE_SMOKE=0 NATURAL_RESCUE_PROOF=0 BROWSER_PROOF=0.

- Customer Comms: Internal operator quality fix; no customer communication required.

- GitHub Status: fixed_pending_release

- Public Response: closed

- Code References: - scripts/release/greenfield_matrix_clarification.py
- tests/unit/install/test_greenfield_matrix_clarification.py
