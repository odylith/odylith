- Bug ID: CB-255

- Status: Open

- Created: 2026-07-16

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The first 240-case discovery case was correctly rejected before confirmation because the accepted-project memory preview projected clipped or dangling proof-obligation copy.

- Impact: A viable consumer utility prompt fails pre-confirm instead of compiling a transaction, blocking creation without giving the user a usable path.

- Components Affected: odylith

- Environment(s): Installed 0.1.15 seeded discovery matrix, 240-case high-variance campaign.

- Detected By: Fail-fast installed high-variance campaign.

- Failure Signature: generated_copy_quality: accepted-project memory preview leaked clipped or dangling public copy at proof_obligations[0].required_evidence.

- Trigger Path: repair-library-borrow-path from tests/fixtures/greenfield-volume/consumer-creative-community.v1.json.

- Ownership: Artifact plan projector accepted-project projection.

- Timeline: Captured 2026-07-16 through `odylith bug capture`.

- Blast Radius: Any greenfield proposal whose proof obligation is projected with a clipped required_evidence fragment.

- SLO/SLA Impact: Pre-confirm compilation rejects a user request; post-confirm safety remains intact.

- Data Risk: No governed write occurred; no persisted product data affected.

- Security/Compliance: No security or compliance impact.

- Invariant Violated: Pre-confirm package must contain complete, grammatical human-visible copy before confirmation.

- Root Cause: Under investigation; the package-quality gate identified the accepted-project proof-obligation projection as the failing owner.

- Solution: Repair the shared accepted-project projection or its upstream semantic fragment, add the exact regression, replay the failed subset, then resume volume discovery.

- Rollback/Forward Fix: Forward fix only; no accepted transaction or governed records were written.

- Verification: Exact failed-subset installed replay must pass with zero generated-copy findings before resuming the 240-case campaign.

- Prevention: Keep generated-copy quality in the pre-confirm gate and cover the repair-library proof obligation directly.

- Agent Guardrails: Do not downgrade the gate or create post-confirm repair; fix the pre-confirm projection source.

- Preflight Checks: Inspect the staged accepted-project proof obligation and reproduce the package-quality finding.

- Regression Tests Added: The exact failed-subset replay file is persisted at odylith-release-proof-8f66d1777/failed-subset-replay/failed-subset-001.cases.json.

- Monitoring Updates: The campaign failure-response packet records the cluster and failed-subset replay file.

- Version/Build: 0.1.15 installed artifact from source checkpoint 8f66d1777.

- Config/Flags: 240-case discovery, seeded install, four workers, stop after one failure cluster, browser and rescue proof omitted by discovery tier.

- Customer Comms: Internal quality remediation; no user-facing incident because no transaction was confirmed.

- GitHub Status: confirmed

- Public Response: closed

- Code References: - scripts/release/greenfield_preconfirm_matrix.py
- src/odylith/runtime/artifact_quality/greenfield_package_quality.py
