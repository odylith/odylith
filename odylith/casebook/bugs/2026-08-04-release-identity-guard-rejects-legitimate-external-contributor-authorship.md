- Bug ID: CB-320

- Status: Open

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Always

- Type: CI

- Description: The history identity validator required every reachable commit to use the freedom-research maintainer identity. Legitimate commits from external human contributors therefore failed pull-request CI, and the written policy encouraged rewriting immutable contributor authorship instead of preserving credit.

- Impact: External contributors cannot pass the identity job or retain authorship under the documented merge policy.

- Components Affected: release

- Environment(s): Odylith product-repo pull_request, release-candidate, and release workflows using scripts/validate_git_identity.py history

- Detected By: Adversarial review of external PR #32 followed by direct identity-validator reproduction

- Failure Signature: validate_git_identity.py history exits 1 for thejesh23-authored commits solely because the author is not freedom-research

- Trigger Path: python scripts/validate_git_identity.py history --repo-root . 94e1f5268668d63b25f6fc11bf970030854faa27

- Ownership: Release identity validation and repository contributor policy

- Timeline: Captured 2026-08-04 through `odylith bug capture`.

- Blast Radius: All external human contributors, pull-request identity CI, and maintainer merge decisions

- SLO/SLA Impact: Blocks external contribution delivery and forces unnecessary maintainer-only commit rewriting

- Data Risk: No product data loss; immutable authorship and attribution integrity are at risk

- Security/Compliance: Maintainer credential controls remain necessary, but conflating them with contributor authorship creates governance and attribution risk

- Invariant Violated: External human contributors retain original Git authorship while maintainer credentials and assistant-attribution safeguards remain pinned

- Root Cause: Canonical maintainer identity was incorrectly applied to every commit author instead of only maintainer credentials, maintainer-authored commits, and repository-owned metadata

- Solution: Allow external human authors in history validation, require exact canonical maintainer aliases when used, and continue rejecting assistant/model/tool identities and attribution

- Rollback/Forward Fix: Forward fix on the active v0.1.15 release branch

- Verification: Identity unit suite passes; external PR head passes history validation; canonical maintainer config remains strict; guidance/install parity tests pass

- Prevention: Keep external-human acceptance and assistant-attribution rejection as explicit regression cases

- Agent Guardrails: Never rewrite legitimate external Git authorship to the maintainer identity; separate maintainer credential proof from contribution-history safety

- Preflight Checks: Read CB-070, AGENTS.md, CLAUDE.md, CONTRIBUTING.md, the identity validator, its tests, and all workflow callers together

- Regression Tests Added: tests/unit/test_validate_git_identity.py covers external humans, partial maintainer aliases, assistant identities, human co-authors, and assistant attribution

- Monitoring Updates: The existing pull_request and release identity jobs exercise the revised shared validator

- Version/Build: 2026/freedom/v0.1.15

- Related Incidents/Bugs: CB-070

- Code References: - scripts/validate_git_identity.py
- tests/unit/test_validate_git_identity.py
- src/odylith/install/agents.py

- Runbook References: - AGENTS.md
- CONTRIBUTING.md

- Fix Commit/PR: current branch 2026/freedom/v0.1.15
