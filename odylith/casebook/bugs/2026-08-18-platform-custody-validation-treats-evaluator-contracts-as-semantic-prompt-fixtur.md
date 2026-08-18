- Bug ID: CB-336

- Status: Open

- Created: 2026-08-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: Detached source-local validation fails before code proof because the platform custody loader expands every greenfield-semantic-*.json file, including evaluation contracts that intentionally contain no prompt, packet, or platform_custody_sentinels.

- Impact: Delivery risk: canonical maintainer validation and release proof cannot start, so changes cannot be safely promoted.

- Components Affected: odylith

- Environment(s): product repo detached source-local maintainer worktree

- Detected By: make dev-validate

- Failure Signature: semantic release fixture lacks platform_custody_sentinels: greenfield-semantic-development-evaluation-contract.v1.json

- Trigger Path: make dev-validate -> platform_domain_leakage_check.load_custody_sentinels

- Ownership: release platform custody validation

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: all maintainer source-local validation runs with semantic evaluation contracts present

- SLO/SLA Impact: Release validation availability is zero until the false-positive discovery scope is corrected.

- Data Risk: No product data loss; operational risk is false blocking of all release proof.

- Security/Compliance: Security posture remains fail-closed. Compliance and policy risk is validator scope drift: unrelated contracts are treated as custody evidence, which can pressure maintainers to add ungrounded sentinel metadata.

- Invariant Violated: Custody sentinels must be loaded only from source-grounded semantic prompt fixtures, not unrelated evaluator contracts.

- Workaround: Pass an explicit smoke fixture path to the checker; canonical dev-validate currently does not expose this.

- Root Cause: DEFAULT_FIXTURE_GLOB is broader than the loader's prompt-or-packet fixture contract.

- Solution: Narrow default discovery to greenfield semantic smoke fixtures while retaining explicit fixture_paths for targeted tests.

- Rollback/Forward Fix: Forward fix; do not weaken sentinel grounding validation.

- Verification: Run platform leakage unit tests and make dev-validate past the custody gate.

- Prevention: Pin default discovery to the fixture family that owns prompt/packet custody sentinels.

- Agent Guardrails: Do not weaken sentinel validation or add empty sentinel placeholders to evaluator contracts.

- Related Incidents/Bugs: CB-335

- Code References: - scripts/release/platform_domain_leakage_check.py
