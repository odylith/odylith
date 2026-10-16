- Bug ID: CB-238

- Status: Open

- Created: 2026-07-11

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The installed on-call handoff campaign compiled and committed, but generated release evidence retained only three of four supplied terms because the opening role context 'on-call engineers handing an incident' was discarded.

- Impact: The compiler temporarily withholds CONFIRM for a complete request while preserving the no-post-confirm-failure guarantee.

- Components Affected: odylith

- Environment(s): Fresh locally built installed runtime 0.1.15 from checkpoint 42dad9b1e.

- Detected By: 240-case installed high-variance greenfield campaign

- Failure Signature: domain term coverage too low: expected at least 4, found 3.

- Trigger Path: Installed 240-case campaign case on-call-handoff-ledger.

- Ownership: greenfield_confirmed_prompt_source and greenfield_confirmed_intent_recovery

- Timeline: Captured 2026-07-11 through `odylith bug capture`.

- Blast Radius: Command-led requests that state a human role in a for-role-gerund audience clause.

- SLO/SLA Impact: No post-confirm write failure occurred, but the release campaign cannot make a success claim until the exact replay passes.

- Data Risk: No governed data was written for copy-gate failures; the term-coverage case committed only its validated sealed package.

- Security/Compliance: No security or compliance regression observed.

- Invariant Violated: Every supplied material role or domain term must survive into the compiled governed package or remain explicitly represented.

- Root Cause: Nested for and to relations were treated as first-path wrappers, so the role context was removed before semantic projection.

- Solution: Recover bounded role context from for-role-gerund clauses, ignore nested non-command for and to tail candidates, and anchor generic handoff state phrases to the supplied role.

- Rollback/Forward Fix: Forward fix only; retain the pre-confirm quality gate as a fail-closed defense.

- Verification: Focused regression passes, source package reproduces cleanly, then a fresh installed runtime replays the exact failed subset before the full campaign resumes.

- Prevention: Keep user evidence authoritative, repair shared producers before CONFIRM, and retain exact high-variance campaign fixtures.

- Agent Guardrails: Do not lower quality thresholds, suppress the issue, or move it after CONFIRM. Repair the upstream shared compiler rule.

- Preflight Checks: The exact failed-subset replay must pass from a freshly built installed runtime.

- Regression Tests Added: tests/unit/runtime/test_greenfield_live_simulation_regressions.py::test_on_call_role_context_is_preserved_in_the_compiled_package

- Monitoring Updates: The release campaign records this failure cluster until the exact replay and full corpus pass.

- Version/Build: 0.1.15-42dad9b1e

- Config/Flags: GREENFIELD_MATRIX_DEEP_VOLUME_MAX_WORKERS=6; pre-confirm compiler tribunal enabled.

- Customer Comms: No user clarification is required; the compiler repairs the supplied evidence path internally.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_prompt_source.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_recovery.py
