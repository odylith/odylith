- Bug ID: CB-016

- Status: Open

- Created: 2026-03-28

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: `make release-preflight` reused the shared repo `dist/`
  directory, so stale Odylith wheels from prior local builds caused the
  hosted-asset publisher to fail closed before it could assemble or smoke the
  current release candidate.

- Impact: Maintainer validation could fail for an avoidable local hygiene
  reason even when the current candidate build and hosted-asset contract were
  otherwise correct. That made the new pre-dispatch proof gate less robust
  than intended.

- Components Affected: `bin/release-preflight`, release asset publisher,
  maintainer release proof lane, release asset staging contract.

- Environment(s): product repo maintainer checkout with more than one Odylith
  wheel present under `dist/`.

- Root Cause: The publisher correctly required exactly one Odylith wheel in its
  input directory, but `release-preflight` staged into the long-lived shared
  `dist/` tree instead of an isolated temporary output directory.

- Solution: Keep the publisher strict, but make `release-preflight` build and
  publish from a private temp dist directory, verify the wheel there, and run
  the local hosted-asset smoke against that isolated asset set.

- Verification: Source fix landed with a regression test, and manual branch
  rehearsal now uses isolated preflight output instead of relying on `dist/`
  cleanup.

- Prevention: Do not let maintainer release proof depend on ambient local
  artifact cleanup. Any blocking release proof should stage its own ephemeral
  build output and clean it up automatically.

- Detected By: Manual hosted-asset proof rehearsal while implementing the
  relaunch reset on `2026/freedom/release-reset-runtime-footprint`.

- Failure Signature: the release asset publisher raised
  `ValueError("expected exactly one odylith wheel in dist/")` during
  preflight-style local proof.

- Trigger Path: `make release-preflight VERSION=0.1.0` or equivalent local
  asset publish steps after earlier wheel builds left stale Odylith wheels in
  `dist/`.

- Ownership: Release proof and asset staging contract.

- Timeline: The relaunch work strengthened the publisher contract to reject
  ambiguous wheel input, which then exposed that preflight was still reusing a
  shared artifact directory.

- Blast Radius: Maintainers cutting preview releases from a working tree with
  leftover local build artifacts.

- SLO/SLA Impact: Release proof reliability degrades and operator time is lost
  on manual artifact cleanup.

- Data Risk: None.

- Security/Compliance: The strict single-wheel publisher check is correct and
  should remain in place.

- Invariant Violated: The canonical release proof lane should be deterministic
  and self-contained, not sensitive to stale local artifacts from prior runs.

- Workaround: Clean `dist/` manually before rerunning preflight. This is no
  longer required after the forward fix.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not weaken the publisher’s single-wheel guard to hide
  this problem. Fix the staging environment instead.

- Preflight Checks: Inspect this bug, the Release component spec, and the
  hosted-asset proof lane before changing preflight staging behavior again.

- Regression Tests Added: `tests/unit/install/test_release_bootstrap.py`

- Monitoring Updates: None.

- Related Incidents/Bugs: `2026-03-28-full-stack-managed-runtime-payloads-are-too-large-for-install-and-upgrade.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: `make release-preflight VERSION=0.1.0`

- Customer Comms: None. This is a maintainer-lane reliability issue.

- Code References: `bin/release-preflight`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`,
  `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: Pending.
