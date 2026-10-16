- Bug ID: CB-291

- Status: Open

- Created: 2026-07-23

- Severity: P1

- Reproducibility: Always

- Type: OperatorUX

- Description: A user can CONFIRM a sealed Greenfield transaction successfully, receive a five-line receipt, and still have no visible route to the generated governance home or its Radar, Registry, Atlas, and Compass views. A local user repro also exposed a package that passed machine quality gates while containing an invalid actor, fractured prose, stale generic guidance, and a transient prewrite path.

- Impact: First-time users cannot discover or inspect the governance package they just accepted; misleading quality success can cause them to trust a plan that is not ready for implementation.

- Components Affected: domain-intelligence

- Environment(s): Pinned 0.1.15 installed consumer repo via Codex and Claude-compatible Greenfield flow.

- Detected By: Direct first-time local install reproduction and adversarial artifact review.

- Failure Signature: Successful greenfield create prints transaction, gates, sealed writes, and readback only; it omits odylith/index.html and all governed-surface routes.

- Trigger Path: odylith greenfield propose -> CONFIRM -> odylith greenfield create --confirm

- Ownership: Greenfield confirmation presentation contract and domain-intelligence quality gate.

- Timeline: Captured 2026-07-23 through `odylith bug capture`.

- Blast Radius: Every first-time Greenfield confirmation across Codex, Claude Code, and direct CLI use.

- SLO/SLA Impact: Onboarding comprehension, review completion, and trusted implementation readiness are degraded.

- Data Risk: No user data loss; governance artifact quality and local path custody are affected.

- Security/Compliance: No external security exposure; local temporary path disclosure violates evidence-custody expectations.

- Invariant Violated: After CONFIRM, the user must receive one deterministic, host-agnostic route to the committed governance home and must not be told a package is quality-passed when it contains obvious semantic or visible-copy defects.

- Workaround: Open odylith/index.html manually and audit the generated source files before planning implementation.

- Root Cause: The commit-only CLI projected only a transaction receipt; host guidance did not require navigation handoff, and the quality gate did not reject invalid actor extraction or visible fractured prose in this scenario.

- Solution: Emit a deterministic post-confirm navigation contract in text and JSON, require host-neutral relay guidance, and add a targeted quality regression for this intent shape.

- Rollback/Forward Fix: Forward fix only; do not reopen post-confirm generation or repair.

- Verification: Focused CLI and guidance tests plus an installed consumer reproduction must show one navigation block after success and no navigation on failure.

- Prevention: Treat first-time post-confirm discovery and visible semantic quality as release-quality gates.

- Agent Guardrails: Do not end a confirmed Greenfield flow with a receipt alone. Surface the committed governance home and distinguish committed planning from implemented product work.

- Preflight Checks: Inspect the actual generated governance home, source artifacts, and confirmation transcript; do not rely only on matrix scores.

- Regression Tests Added: tests/unit/runtime/test_greenfield_cli_paths.py::test_greenfield_create_cli_applies_confirmed_prompt covers the baseline successful commit path; the fix adds an exact navigation assertion there.

- Monitoring Updates: Track post-confirm handoff presence in installed Greenfield matrix output.

- Version/Build: 0.1.15 pinned release

- Config/Flags: Local Codex consumer install, no host-specific renderer.

- Customer Comms: Acknowledge the missing navigation and clearly state that the generated package requires review before implementation.

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_create_cli.py
- tests/unit/runtime/test_greenfield_cli_paths.py
