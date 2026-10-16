- Bug ID: CB-172

- Status: FixedPendingRelease

- Created: 2026-05-06

- Severity: P1

- Reproducibility: Always

- Type: Tooling

- Description: Structured sync action results can crash governed sync execution

- Impact: A governed sync plan can perform the correct mutation and then crash before completing because the full sync executor coerces structured action results with int(...), while dashboard refresh accepts the same structured action mapping. Operators see a failed sync even when the underlying refresh step succeeded.

- Components Affected: sync

- Environment(s): Odylith product repo branch 2026/freedom/v0.1.15 while validating selective release-event sync.

- Detected By: Maintainer selective-sync validation for release traceability freshness.

- Failure Signature: odylith sync --impact-mode selective odylith/radar/source/releases/release-assignment-events.v1.jsonl rebuilt the traceability graph, then raised TypeError: int() argument must be a string, a bytes-like object or a real number, not 'dict' from _execute_plan.

- Trigger Path: src/odylith/runtime/governance/sync_workstream_artifacts.py

- Ownership: Governed sync executor action-result contract.

- Timeline: Found while fixing release traceability freshness: selective release-event sync entered the correct four-step plan, rebuilt the graph, then crashed in the executor because the action returned a mapping.

- Blast Radius: Any full governed sync step implemented as an action returning a structured mapping can fail after doing useful work, causing false failure states and forcing manual reruns.

- SLO/SLA Impact: Sync reliability and wall-clock recovery degrade because successful action steps can report as process failures.

- Data Risk: Generated governance outputs may be partially updated before the crash, making the operator rerun path harder to reason about.

- Security/Compliance: No security exposure identified; failure affects governance sync integrity and operator recovery.

- Invariant Violated: All governed sync executors must share the same action-result contract and must not crash after a successful structured action result.

- Root Cause: _execute_plan wrapped action calls in int(step.action() or 0) instead of routing through _coerce_callable_step_result, unlike dashboard refresh step execution.

- Solution: Route full sync action results through _coerce_callable_step_result so structured mapping results are accepted consistently.

- Verification: PYTHONPATH=src pytest tests/unit/runtime/test_sync_cli_compat.py::test_execute_plan_accepts_structured_action_results -q; ./.odylith/bin/odylith sync --repo-root . --impact-mode selective odylith/radar/source/releases/release-assignment-events.v1.jsonl

- Prevention: Keep parity tests for structured action results across dashboard refresh and full governed sync execution.

- Regression Tests Added: tests/unit/runtime/test_sync_cli_compat.py::test_execute_plan_accepts_structured_action_results

- Fixed In: 0.1.15
