- Bug ID: CB-236

- Status: Open

- Created: 2026-07-11

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The installed wedding-weekend campaign treated the audience context 'guests traveling to a small town' as the first path action. It then derived a clipped actor ending in 'a' in staged Radar ownership prose, so pre-confirm package validation stopped safely.

- Impact: The compiler temporarily withholds CONFIRM for a complete request while preserving the no-post-confirm-failure guarantee.

- Components Affected: odylith

- Environment(s): Fresh locally built installed runtime 0.1.15 from checkpoint 42dad9b1e.

- Detected By: 240-case installed high-variance greenfield campaign

- Failure Signature: Radar workstream has a clipped article phrase ending in a.

- Trigger Path: Installed 240-case campaign case wedding-weekend-guest-guide.

- Ownership: greenfield_confirmed_prompt_source and greenfield_first_path_semantics

- Timeline: Captured 2026-07-11 through `odylith bug capture`.

- Blast Radius: Prompt-led products whose opening sentence describes an audience with a gerund before the real first action.

- SLO/SLA Impact: No post-confirm write failure occurred, but the release campaign cannot make a success claim until the exact replay passes.

- Data Risk: No governed data was written for copy-gate failures; the term-coverage case committed only its validated sealed package.

- Security/Compliance: No security or compliance regression observed.

- Invariant Violated: A descriptive audience clause cannot become a first-path action, human actor, or rendered ownership label.

- Root Cause: Prompt recovery accepted the leading gerund as an action and an unbounded for...that span as an actor.

- Solution: Drop leading contextual gerund sentences, reject unbounded prompt actor shortcuts, and preserve only bounded role context.

- Rollback/Forward Fix: Forward fix only; retain the pre-confirm quality gate as a fail-closed defense.

- Verification: Focused regression passes, source package reproduces cleanly, then a fresh installed runtime replays the exact failed subset before the full campaign resumes.

- Prevention: Keep user evidence authoritative, repair shared producers before CONFIRM, and retain exact high-variance campaign fixtures.

- Agent Guardrails: Do not lower quality thresholds, suppress the issue, or move it after CONFIRM. Repair the upstream shared compiler rule.

- Preflight Checks: The exact failed-subset replay must pass from a freshly built installed runtime.

- Regression Tests Added: tests/unit/runtime/test_greenfield_live_simulation_regressions.py::test_wedding_context_phrase_does_not_become_the_first_path_actor

- Monitoring Updates: The release campaign records this failure cluster until the exact replay and full corpus pass.

- Version/Build: 0.1.15-42dad9b1e

- Config/Flags: GREENFIELD_MATRIX_DEEP_VOLUME_MAX_WORKERS=6; pre-confirm compiler tribunal enabled.

- Customer Comms: No user clarification is required; the compiler repairs the supplied evidence path internally.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_prompt_source.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_semantics.py
