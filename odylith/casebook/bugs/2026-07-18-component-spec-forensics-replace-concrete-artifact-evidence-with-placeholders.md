- Bug ID: CB-284

- Status: Open

- Created: 2026-07-18

- Severity: P2

- Reproducibility: Always

- Type: DataLoss

- Description: The component-spec sync derives a high-confidence forensic timeline from mapped Compass events but replaces every supplied artifact reference with synthetic tracked_artifact_N labels. This produces a count without a verifiable evidence identity and weakens the paired Requirements Trace. Operational risk: release and audit decisions can rely on non-verifiable governance evidence. Security posture: no secret or authorization exposure is observed. Privacy and compliance posture: the forward fix must retain a stable hash for unsafe paths rather than disclose them.

- Impact: Maintainers cannot verify which implementation artifacts support a generated component requirement or forensic row.

- Components Affected: registry

- Environment(s): Odylith product repo source-local governance sync

- Detected By: Independent adversarial review after installed Greenfield proof

- Failure Signature: FORENSICS.v1.json contains tracked_artifact_N instead of supplied event artifacts

- Trigger Path: PYTHONPATH=src .venv/bin/python -m odylith.cli governance sync-component-spec-requirements --repo-root .

- Ownership: Registry governance sync

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: All component dossiers refreshed from mapped events with artifacts

- SLO/SLA Impact: Delivery and audit risk: governance evidence cannot be treated as audit-quality traceability

- Data Risk: Evidence identity is discarded from derived source truth; source event remains available

- Security/Compliance: Security posture: no direct secret exposure. Privacy policy: unsafe artifact paths must be represented by a deterministic hash.

- Invariant Violated: Generated governance evidence must remain traceable to concrete source artifacts without leaking sensitive path terms.

- Root Cause: sync_component_spec_requirements._forensics_timeline_row intentionally substitutes positional placeholder labels for event.artifacts.

- Solution: Persist privacy-safe deterministic artifact references and render them in the requirement trace; preserve hashes for unsafe paths.

- Rollback/Forward Fix: Forward fix the generator and refresh affected Registry/Compass surfaces; do not hand-edit generated dossiers.

- Verification: Regression tests cover safe source paths, hashed unsafe paths, and regenerated dossiers.

- Prevention: Generated forensics must never publish placeholder evidence when a source event carries an artifact identity.

- Agent Guardrails: Do not accept counts or generic prose as evidence custody; inspect generated forensic artifact identities.

- Preflight Checks: Run component-spec sync check-only and inspect the refreshed forensics evidence rows.

- Version/Build: 0.1.15 source-local

- Related Incidents/Bugs: CB-243, CB-266

- Code References: - src/odylith/runtime/governance/sync_component_spec_requirements.py
