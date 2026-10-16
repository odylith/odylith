- Bug ID: CB-186

- Status: FixedPendingRelease

- Created: 2026-05-08

- Severity: P2

- Reproducibility: High

- Type: UX

- Description: Greenfield propose/create produced richer governance, but the post-apply handoff still centered the first coding workstream instead of making project-first direction choices, customization options, architecture review, and coding-readiness gates the next operator action.

- Impact: Operators in empty or thin repos can accept a proposal and be pushed toward implementation before deciding runtime, data posture, architecture depth, proof bar, non-goals, or regulated/safety boundaries.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo maintainer lane, v0.1.15 greenfield create/apply path, 2026-05-08.

- Detected By: Operator feedback requesting greenfield to build a deep comprehensive project first and not jump into coding.

- Failure Signature: greenfield create closeout printed the exact first coding workstream and next coding prompt as the primary handoff while project customization choices and coding-readiness gates were not first-class proposal data.

- Trigger Path: odylith greenfield propose/create --prompt '<greenfield project>' --release 0.0.1 --confirm, then inspect proposal text and apply closeout.

- Ownership: Domain Intelligence proposal scaffold, project brief normalization, proposal validation, proposal rendering, greenfield apply next-steps, and installed greenfield guidance.

- Timeline: Captured 2026-05-08 through `odylith bug capture`.

- Blast Radius: Fresh greenfield consumer journeys across CLI, Codex, Claude Code, Radar, Registry, Atlas, Compass, and release handoff.

- SLO/SLA Impact: Release-quality greenfield UX regresses because operators spend extra turns correcting project direction after Odylith has already implied coding should start.

- Data Risk: No direct data loss; early implementation can under-model sensitive data, safety, regulated posture, fixture policy, and evidence boundaries before source exists.

- Security/Compliance: Security and compliance risk increases when greenfield first-wave posture omits explicit pre-coding choices for auth, privacy, audit, non-custody, safety, or regulated review.

- Invariant Violated: Greenfield apply creates governed project truth; it must not be treated as permission to start coding until project-first direction choices and coding-readiness gates are accepted.

- Root Cause: The prior apply handoff modeled next_steps as an implementation runway only. The canonical proposal did not require a top-level project-first brief, so validation and CLI output could pass while still centering coding.

- Solution: Add a top-level project_brief with blueprint sections, customization options, pre-coding checkpoints, coding-readiness gates, and host-independent paths. Normalize legacy proposals with the brief, validate it, render it before backlog, and make create/apply closeout lead with project-first workstream and later coding prompt.

- Rollback/Forward Fix: Forward fix in Domain Intelligence; no consumer migration required because legacy proposals are normalized with a synthesized project_brief before validation/apply.

- Verification: PYTHONPATH=src pytest -q tests/unit/runtime/test_greenfield_proposals.py passed with 33 tests after adding project-first coverage.

- Prevention: Keep proposal validation requiring project_brief and tests asserting Project-first blueprint appears before Backlog proposal, robot swarm has simulation/safety customization, and CLI closeout prints project-first workstream before eventual first coding workstream.

- Agent Guardrails: Agents should treat greenfield create/apply as project governance formation. They may plan coding only after direction options and readiness gates are accepted or explicitly waived by the operator.

- Preflight Checks: Run greenfield propose text/JSON checks plus greenfield create/apply closeout checks before releasing Domain Intelligence changes.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_validation_rejects_missing_project_first_brief; tests/unit/runtime/test_greenfield_proposals.py::test_robot_swarm_project_brief_blocks_coding_rush; updated greenfield prompt/CLI/create assertions.

- Monitoring Updates: Casebook tracks this UX regression as a greenfield release-quality blocker until source and bundled guidance ship.

- Version/Build: v0.1.15 maintainer branch

- Config/Flags: source-local maintainer mode

- Customer Comms: Operator-facing greenfield text now says project-first and does not present coding as the immediate next action.

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_project_brief.py
- src/odylith/runtime/domain_intelligence/proposal_scaffold.py
- src/odylith/runtime/domain_intelligence/proposal_normalization.py
- src/odylith/runtime/domain_intelligence/proposal_validation.py
- src/odylith/runtime/domain_intelligence/proposal_rendering.py
- src/odylith/runtime/domain_intelligence/greenfield_experience.py
- src/odylith/runtime/domain_intelligence/greenfield_cli_output.py
