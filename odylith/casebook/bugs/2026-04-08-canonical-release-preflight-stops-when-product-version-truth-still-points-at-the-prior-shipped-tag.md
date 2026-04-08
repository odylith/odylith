- Bug ID: CB-073

- Status: Closed

- Created: 2026-04-08

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Canonical `make release-preflight VERSION=0.1.10` on clean
  `main` failed even after the `v0.1.10` release-note and benchmark-override
  truth were in place, because tracked product version truth still advertised
  `0.1.9` in `pyproject.toml`, `src/odylith/__init__.py`, and the checked-in
  product pin.

- Impact: The canonical GA lane could not initialize the `v0.1.10` release
  session or dispatch the release until maintainer source truth was advanced to
  the intended version.

- Components Affected: `pyproject.toml`, `src/odylith/__init__.py`,
  `odylith/runtime/source/product-version.v1.json`, canonical
  `make release-preflight`, release component contract, maintainer release
  workflow truth.

- Environment(s): Odylith product repo maintainer mode, canonical `main`,
  pinned dogfood release prep for `v0.1.10`.

- Root Cause: The release-prep branch landed release notes, popup proof, and
  benchmark-override truth, but the tracked product version itself was never
  advanced from `0.1.9` to `0.1.10`. Canonical preflight correctly fail-closed
  once it compared the requested tag version against `pyproject.toml` and the
  tracked product pin.

- Solution: Advance canonical version truth to `0.1.10` in
  `pyproject.toml`, regenerate `src/odylith/__init__.py` and
  `odylith/runtime/source/product-version.v1.json` from that source version,
  and record the maintainer rule that authored notes or overrides do not
  replace the required tracked version bump.

- Verification: `PYTHONPATH=src python3 -m odylith.runtime.governance.version_truth --repo-root . check`;
  `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_version_truth.py tests/unit/runtime/test_validate_self_host_posture.py`;
  canonical `make release-preflight VERSION=0.1.10` after merge back to
  `main`.

- Prevention: Before canonical release preflight, land the intended
  `pyproject.toml` version and sync package plus tracked product pin truth on
  the release branch. Release notes, overrides, and the explicit `VERSION=`
  argument do not reserve a release version by themselves.

- Detected By: Canonical `make release-preflight VERSION=0.1.10` on 2026-04-08.

- Failure Signature: `odylith self-host release contract FAILED` with
  `expected release tag version '0.1.10' does not match tracked product pin '0.1.9'`
  and `expected release tag version '0.1.10' does not match pyproject.toml version '0.1.9'`.

- Trigger Path: Run canonical release preflight for the next version after
  landing release-note and override truth but before advancing tracked product
  version truth.

- Ownership: Release component contract, maintainer release workflow truth,
  tracked version-source discipline.

- Timeline: surfaced on 2026-04-08 while moving the merged `v0.1.10` branch
  from CI-ready state into canonical preflight on `main`.

- Blast Radius: Canonical release session initialization, tag reservation, and
  the entire GA lane for the intended version.

- SLO/SLA Impact: No customer outage; release-lane blocker in a P0 maintainer
  path.

- Data Risk: Low data risk, high release-operations risk because canonical
  release proof cannot begin for the intended version.

- Security/Compliance: Low direct security risk; the issue is source-of-truth
  integrity for release publication.

- Invariant Violated: The requested release tag version must match tracked
  product version truth before preflight can initialize canonical release
  proof.

- Workaround: None acceptable besides performing the missing version bump in
  tracked source truth.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: When release prep changes the versioned public story,
  update governed truth first and then advance the tracked product version in
  `pyproject.toml` with synced package and pin files before returning to
  canonical `main` for preflight.

- Preflight Checks: Compare the requested release tag version with
  `pyproject.toml`, `src/odylith/__init__.py`, and
  `odylith/runtime/source/product-version.v1.json` before blaming the release
  workflow or runtime lane.

- Regression Tests Added: Reused existing version-truth and self-host release
  contract tests; no new product code path was introduced.

- Monitoring Updates: Treat future canonical preflight failures on
  expected-version mismatch as release-truth drift first, not workflow failure.

- Related Incidents/Bugs:
  [2026-04-08-release-proof-tests-assume-local-codex-host-and-break-in-github-actions.md](2026-04-08-release-proof-tests-assume-local-codex-host-and-break-in-github-actions.md)

- Version/Build: branch `2026/freedom/v0.1.10-version-truth` before merge.

- Customer Comms: internal maintainer-only release-truth blocker fix.

- Code References: `pyproject.toml`, `src/odylith/__init__.py`,
  `odylith/runtime/source/product-version.v1.json`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Fix Commit/PR: current branch `2026/freedom/v0.1.10-version-truth`, pending
  commit/push.
