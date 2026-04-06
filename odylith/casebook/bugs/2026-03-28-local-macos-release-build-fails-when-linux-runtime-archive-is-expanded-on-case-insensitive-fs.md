- Bug ID: CB-010

- Status: Open

- Created: 2026-03-28

- Severity: P1

- Reproducibility: Always on affected maintainer filesystems

- Type: Product

- Description: Local maintainer release-asset builds on macOS failed while
  assembling Linux managed runtime bundles because the upstream
  `python-build-standalone` archive was being expanded onto the host
  filesystem. On common case-insensitive macOS filesystems, the Linux terminfo
  tree contains case-distinct paths that cannot be materialized safely.

- Impact: `make release-preflight` could not complete the local hosted-asset
  proof on an affected macOS maintainer machine even though the canonical
  GitHub release workflow runs on Linux. That weakened the maintainer rehearsal
  contract for the restart-at-`v0.1.0` preview lane.

- Components Affected: release asset publisher, managed runtime bundle
  assembly, local maintainer preflight proof lane.

- Environment(s): macOS maintainer checkout on a case-insensitive filesystem
  while building Linux managed runtime bundles for local hosted-asset proof.

- Root Cause: Odylith downloaded the upstream Linux managed Python archive and
  unpacked it onto the macOS host filesystem before repackaging it as an
  Odylith runtime bundle. The upstream archive includes case-distinct terminfo
  paths that are valid in the tarball but not safely materializable on a
  case-insensitive filesystem.

- Solution: Stop expanding foreign-platform upstream runtime archives onto the
  host filesystem during release packaging. Validate the upstream tar members,
  rewrite the root from `python/` to `runtime/`, and stream them directly into
  the Odylith runtime bundle tarball before adding Odylith's overlay files.

- Verification: Focused publisher and bootstrap tests now cover root rewriting
  without extracting case-colliding paths. Maintainer local hosted-asset proof
  remains the final operational close condition for this bug.

- Prevention: Keep foreign-platform runtime bundle assembly stream-based. Do
  not require a maintainer machine to fully unpack another platform's Python
  archive just to publish or preflight Odylith release assets.

- Detected By: Local maintainer release-asset proof on macOS after the split
  managed-runtime relaunch work landed.

- Failure Signature: `publish_release_assets.py` fails during Linux runtime
  bundle assembly with extraction errors under a macOS temp directory while
  processing the upstream managed Python archive.

- Trigger Path: `make release-preflight`, or direct execution of the local
  release asset publisher on macOS.

- Ownership: Release asset build lane and managed runtime bundle assembly.

- Timeline: The relaunch work tightened installer proof and split managed
  assets, which exposed that the local macOS maintainer path still unpacked
  Linux upstream archives onto the host filesystem. Odylith now streams those
  members into the final runtime tarball instead.

- Blast Radius: Local maintainer proof on affected macOS filesystems. Canonical
  release publication on Linux is not the direct failure site, but the local
  release rehearsal contract was degraded until this was fixed.

- SLO/SLA Impact: Maintainer release preflight becomes unreliable on one of the
  primary authoring environments.

- Data Risk: None.

- Security/Compliance: The fix must preserve archive validation and signed
  release evidence handling while changing how runtime bundles are assembled.

- Invariant Violated: The local maintainer proof lane should be able to build
  every supported runtime bundle without depending on host-filesystem quirks.

- Workaround: Run the full release-asset build on a Linux maintainer host.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Do not weaken release proof by skipping Linux bundle
  assembly on macOS. Keep the supported-platform matrix intact in local
  preflight.

- Preflight Checks: Review this bug, the active B-005 plan, and the Release
  component spec before changing runtime-bundle assembly again.

- Regression Tests Added: `tests/unit/install/test_release_bootstrap.py`

- Monitoring Updates: none.

- Related Incidents/Bugs: `2026-03-28-release-preflight-fails-when-dist-contains-stale-wheel.md`,
  `2026-03-28-full-stack-managed-runtime-payloads-are-too-large-for-install-and-upgrade.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: none.

- Customer Comms: none. This is a maintainer-lane correctness bug.

- Code References: release asset publisher, `tests/unit/install/test_release_bootstrap.py`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: Pending.
