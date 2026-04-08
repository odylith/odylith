- Bug ID: CB-070

- Status: Closed

- Created: 2026-04-08

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The canonical release identity guard still encodes a narrow
  compatibility exception for `GitHub <noreply@github.com>` in commit history.
  That means the release lane depends on one observed GitHub squash-merge shape
  instead of a simpler rule about canonical maintainer authorship.

- Impact: Release proof still depends on platform-specific committer metadata
  in canonical `main` ancestry. That keeps `v0.1.10` from making the release
  path boringly trustworthy, because the guard is validating a temporary merge
  artifact instead of the maintainer authorship signal that actually matters.

- Components Affected: `scripts/validate_git_identity.py`,
  `tests/unit/test_validate_git_identity.py`, release workflow identity guard,
  maintainer release contract.

- Environment(s): Odylith product repo maintainer mode, canonical GitHub
  release workflow, local release preflight inspection.

- Root Cause: The release identity script was written around one currently
  observed GitHub merge path and carried that platform-generated committer
  shape forward as an allowed history contract. The release lane never reduced
  the rule back to canonical maintainer authorship.

- Solution: Release-history validation now depends on canonical maintainer
  authorship instead of an explicit GitHub committer exception. Local
  maintainer config remains strict on both author and committer identity, while
  history proof now tolerates only the canonical maintainer email with the
  canonical maintainer name or the immutable historical author alias already in
  older release ancestry.

- Verification: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/test_validate_git_identity.py` (`5 passed`);
  `python3 scripts/validate_git_identity.py history --repo-root . HEAD`
  (exit `0`); `git diff --check`.

- Prevention: Keep local maintainer config strict for both author and
  committer, but keep release-history proof focused on canonical authored
  commits instead of platform-generated committer metadata.

- Detected By: `v0.1.10` release prep while checking remaining known release
  blockers before merging the branch to `main`.

- Failure Signature: `scripts/validate_git_identity.py` explicitly accepts
  `GitHub <noreply@github.com>` and the maintainer runbook/spec still describe
  that as a valid release-history identity shape.

- Trigger Path: inspect `scripts/validate_git_identity.py`, run
  `python scripts/validate_git_identity.py history --repo-root . HEAD`, or read
  the release workflow and maintainer release runbook.

- Ownership: Release identity validation and maintainer release contract.

- Timeline: surfaced again during the `v0.1.10` release-hardening lane after
  the benchmark override was recorded and before canonical merge to `main`.

- Blast Radius: canonical release preflight, release workflow gating, and
  maintainer trust in the canonical release identity story.

- SLO/SLA Impact: no customer outage, but a P0 release-integrity gap.

- Data Risk: low source-data risk, medium governance and release-authority risk.

- Security/Compliance: low direct security risk, but it weakens the precision
  of maintainer release-authority proof.

- Invariant Violated: Canonical release history should not depend on a
  temporary GitHub-generated committer exception when canonical maintainer
  authorship is the real release identity signal.

- Workaround: none clean. The current workaround is the exact exception this
  bug exists to remove.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not replace the GitHub-specific exception with a new
  platform-specific committer allowlist. Remove the dependency on committer
  metadata instead.

- Preflight Checks: inspect
  [validate_git_identity.py](../../../scripts/validate_git_identity.py),
  [test_validate_git_identity.py](../../../tests/unit/test_validate_git_identity.py),
  and [release.yml](../../../.github/workflows/release.yml) together before
  changing release identity policy.

- Regression Tests Added:
  `tests/unit/test_validate_git_identity.py` now covers canonical maintainer
  author acceptance with GitHub-generated committer metadata plus the retained
  historical maintainer author alias.

- Monitoring Updates: watch future release prep for any regression where
  history validation reintroduces platform-specific committer allowlists.

- Related Incidents/Bugs:
  [2026-04-08-pinned-dogfood-proof-benchmark-can-wedge-mid-corpus-and-block-release-proof.md](2026-04-08-pinned-dogfood-proof-benchmark-can-wedge-mid-corpus-and-block-release-proof.md)

- Version/Build: branch `2026/freedom/v0.1.10` before canonical merge.

- Customer Comms: internal maintainer-only release integrity fix.

- Code References: `scripts/validate_git_identity.py`,
  `tests/unit/test_validate_git_identity.py`, `.github/workflows/release.yml`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Fix Commit/PR: current branch `2026/freedom/v0.1.10`, pending commit/push.
