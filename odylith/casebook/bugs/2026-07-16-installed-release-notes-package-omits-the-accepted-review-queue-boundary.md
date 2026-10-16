- Bug ID: CB-260

- Status: Open

- Created: 2026-07-16

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The fresh installed CB-259 replay returns and commits a validated ProductCreateTransaction, but the matrix rejects its generated package because the explicit first-release requirement review queue is absent from governed readback.

- Impact: A viable release-notes product cannot pass the pre-confirm domain-quality tribunal, despite an unambiguous user-stated requirement.

- Components Affected: domain-intelligence

- Environment(s): Fresh installed 0.1.15 distribution built from the current 2026/freedom/v0.1.15 working tree.

- Detected By: Installed CB-259 failed-subset matrix replay.

- Failure Signature: domain.term.coverage.too.low.expected.least.found; required term review queue has no readback hits.

- Trigger Path: scripts/release/greenfield_preconfirm_matrix.py with cli-extension-release-notes.

- Ownership: Greenfield typed-intent recovery and proof-boundary preservation.

- Timeline: Captured 2026-07-16 through `odylith bug capture`.

- Blast Radius: Any consumer prompt whose affirmative first-release boundary is not part of the first actor action.

- SLO/SLA Impact: Pre-confirm tribunal rejects the package before the user receives a clean confirmation rail.

- Data Risk: No incorrect governed write is accepted; the quality tribunal fails closed.

- Security/Compliance: No security or compliance impact.

- Invariant Violated: Every explicit affirmative first-release commitment must survive as a typed, hash-bound product fact before confirmation.

- Root Cause: intent_hypothesis_from_operator_evidence recovers only the first actor action, evidence anchors, and site or time constraints. It omits affirmative first-release-boundary clauses such as a review queue before semantic compilation.

- Solution: Append bounded affirmative first-release requirements to the typed proof boundary during prompt recovery, preserving the terms without changing first-path action semantics or weakening domain-term quality checks.

- Rollback/Forward Fix: Forward-fix only; keep the tribunal fail-closed until the requirement survives typed intent and governed readback.

- Verification: Add exact fixture regressions through typed intent and proposal semantic model, rebuild the distribution, replay the one-case installed matrix, then resume discovery.

- Prevention: Treat explicit release-boundary requirements as accepted product facts, not optional prose or renderer decoration.

- Agent Guardrails: Do not relax required-term coverage, patch a single rendered artifact, or force release-boundary capabilities into the first-path action.

- Preflight Checks: Fresh installed replay must find review queue in a scored governed surface and pass the full quality tribunal.

- Version/Build: 0.1.15 local distribution.

- Config/Flags: install-mode=full; proof-tier=discovery; CB-259 one-case subset.

- Customer Comms: No customer communication; the invalid package was rejected before user confirmation.

- Related Incidents/Bugs: CB-259.

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_recovery.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py

- Runbook References: - odylith/MAINTAINER_RELEASE_RUNBOOK.md
