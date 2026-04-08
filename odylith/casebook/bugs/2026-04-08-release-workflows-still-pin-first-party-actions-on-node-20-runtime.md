- Bug ID: CB-071

- Status: Closed

- Created: 2026-04-08

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The canonical release, release-candidate, and test workflows
  still pin first-party GitHub Actions revisions that execute on the Node 20
  runtime. GitHub now warns about that deprecation during release proof, so the
  shipped release lane still looks stale even when the release logic itself is
  healthy.

- Impact: Maintainer release proof keeps carrying noisy deprecation warnings in
  core CI lanes. That weakens operator trust in the release path and risks a
  future hard failure if the first-party action runtime cutoff lands before the
  next pin refresh.

- Components Affected: `.github/workflows/release.yml`,
  `.github/workflows/release-candidate.yml`, `.github/workflows/test.yml`,
  maintainer release workflow pin policy, release component contract.

- Environment(s): Odylith product repo maintainer mode, GitHub Actions release
  and PR CI, `v0.1.10` release prep.

- Root Cause: The workflows were still pinned to `actions/checkout v4.3.1` and
  `actions/setup-python v5.6.0`, which are immutable but now sit on the older
  Node 20 runtime. Release hardening had already identified the warning, but
  the workflow pins had not yet been refreshed to newer immutable SHAs.

- Solution: Release, release-candidate, and test now pin
  `actions/checkout v5.0.1` and `actions/setup-python v6.1.0` at immutable
  SHAs. Maintainer guidance, release runbook, Radar, and the release component
  spec now treat first-party workflow runtime posture as part of the release
  contract instead of incidental CI drift.

- Verification: `ruby -e 'require "yaml"; %w[.github/workflows/release.yml
  .github/workflows/release-candidate.yml .github/workflows/test.yml].each
  { |f| YAML.load_file(f) }; puts "workflow-yaml-ok"'`
  (`workflow-yaml-ok`); `git diff --check`; direct inspection of the refreshed
  immutable SHAs in the three workflow files.

- Prevention: Treat first-party GitHub Actions runtime posture as part of the
  canonical release contract, not just routine CI housekeeping.

- Detected By: `v0.1.10` release prep while closing the remaining release-lane
  hardening items before GA.

- Failure Signature: GitHub Actions warns that the pinned first-party actions
  still rely on the Node 20 runtime during release or release-candidate proof.

- Trigger Path: inspect `.github/workflows/release.yml`,
  `.github/workflows/release-candidate.yml`, or `.github/workflows/test.yml`,
  then compare pinned SHAs with current upstream Node-safe action releases.

- Ownership: Release workflow pins, maintainer release CI hygiene, release
  component spec.

- Timeline: surfaced from `v0.1.9` release feedback and carried into `v0.1.10`
  release prep on 2026-04-08.

- Blast Radius: Release proof credibility, PR/candidate CI clarity, and future
  GitHub Actions compatibility for the canonical release lane.

- SLO/SLA Impact: No customer outage, but a release-hardening gap in a core
  maintainer lane.

- Data Risk: Low source-data risk, medium release-operations risk if the
  warning ages into a hard platform cutoff.

- Security/Compliance: Low direct risk; the main issue is release-lane
  integrity and maintainability.

- Invariant Violated: Canonical release CI should not ship with known platform
  runtime deprecation warnings on first-party workflow dependencies.

- Workaround: None clean beyond accepting the warning. The real fix is to bump
  the immutable first-party action SHAs.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not replace immutable SHA pins with floating tags while
  updating the workflows.

- Preflight Checks: Inspect
  [release.yml](../../../.github/workflows/release.yml),
  [release-candidate.yml](../../../.github/workflows/release-candidate.yml),
  [test.yml](../../../.github/workflows/test.yml), and the release component
  spec before changing workflow pins.

- Regression Tests Added: None. This slice is declarative workflow-pin
  hardening; proof is the immutable SHA refresh plus YAML parse validation.

- Monitoring Updates: Watch future GitHub Actions release notes for first-party
  action runtime deprecations that would put the canonical release lane back
  into warning-only drift.

- Related Incidents/Bugs:
  [2026-04-08-release-identity-guard-still-depends-on-github-generated-committer-metadata.md](2026-04-08-release-identity-guard-still-depends-on-github-generated-committer-metadata.md)
  [2026-04-08-pinned-dogfood-proof-benchmark-can-wedge-mid-corpus-and-block-release-proof.md](2026-04-08-pinned-dogfood-proof-benchmark-can-wedge-mid-corpus-and-block-release-proof.md)

- Version/Build: branch `2026/freedom/v0.1.10` before canonical merge.

- Customer Comms: internal maintainer-only release CI hardening fix.

- Code References: `.github/workflows/release.yml`,
  `.github/workflows/release-candidate.yml`, `.github/workflows/test.yml`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Fix Commit/PR: current branch `2026/freedom/v0.1.10`, pending commit/push.
