- Bug ID: CB-074

- Status: Closed

- Created: 2026-04-08

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Canonical `v0.1.10` release preflight failed in the hosted
  upgrade smoke because the generated `install.sh` called
  `odylith install --align-pin` after activating the requested runtime. When
  the smoke lane used that script to stand up the prior shipped runtime shape,
  the shipped `0.1.9` CLI rejected the hidden `--align-pin` flag and the local
  release proof stopped before dispatch.

- Impact: Canonical release preflight could not complete the hosted
  `install -> upgrade-cycle -> doctor -> sync` smoke proof for `v0.1.10`,
  blocking release dispatch on an installer-template compatibility regression.

- Components Affected: release asset publisher, local release smoke harness,
  generated `install.sh`, hosted installer upgrade compatibility, release
  component contract.

- Environment(s): Odylith product repo maintainer mode, canonical `main`,
  local hosted release smoke during `make release-preflight VERSION=0.1.10`,
  macOS Apple Silicon.

- Root Cause: The hosted installer template adopted the new hidden
  `install --align-pin` path to converge runtime and pin on existing repos, but
  the canonical upgrade smoke still exercises the candidate installer against
  the last shipped runtime shape. Older shipped CLIs did not expose that hidden
  flag, so the generated installer stopped being compatible with the already
  published version used in upgrade-cycle proof.

- Solution: Keep the generated installer on stable cross-version command
  surfaces only. The template now detects whether the repo already has Odylith
  state and uses `odylith upgrade --to <version> --write-pin` for existing
  installs, while first installs stay on `odylith install --version <version>`.
  Regression proof now checks the generated script for that compatibility
  branch directly.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_release_bootstrap.py`;
  canonical `make release-preflight VERSION=0.1.10` after merge back to
  `main`.

- Prevention: Generated hosted installer templates must not depend on hidden or
  newly introduced CLI flags unless the release lane proves that the exact
  command is safe against the last shipped runtime used in upgrade smoke.

- Detected By: Canonical `make release-preflight VERSION=0.1.10` local release
  smoke on 2026-04-08.

- Failure Signature: `odylith: error: unrecognized arguments: --align-pin`
  while local release smoke uses the generated `install.sh` to stand up the
  previous shipped version during upgrade-cycle proof.

- Trigger Path: Run release preflight for `v0.1.10` after generating a hosted
  installer template that always calls `install --align-pin`.

- Ownership: Hosted installer publication flow, release smoke compatibility,
  release component contract.

- Timeline: surfaced after the canonical version-truth fix landed and preflight
  progressed into local hosted release smoke for `v0.1.10`.

- Blast Radius: Canonical release preflight, local hosted release smoke, and
  trust in the hosted installer’s backward-compatibility story.

- SLO/SLA Impact: No customer outage; release-lane blocker in a P0 maintainer
  path.

- Data Risk: Low data risk, high release-operations risk.

- Security/Compliance: Low direct security risk; the issue is release-proof and
  hosted-installer compatibility integrity.

- Invariant Violated: Hosted installer generation must stay compatible with the
  prior shipped runtime shape used in canonical upgrade-cycle proof.

- Workaround: None acceptable besides patching the installer template or
  weakening smoke realism.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: When maintainer-only installer generation starts using a
  new hidden CLI flag, prove it against the last shipped runtime before letting
  release smoke rely on it. Prefer stable public commands when the installer
  must bridge multiple shipped versions.

- Preflight Checks: Inspect generated `install.sh`, compare its activation
  command with the CLI flags available in the last shipped runtime, and confirm
  the upgrade-cycle smoke path is exercising a realistic prior-version posture
  before editing the template.

- Regression Tests Added: Generated install-script contract coverage now proves
  the fresh-install versus existing-install branch and rejects unconditional
  `--align-pin` usage.

- Monitoring Updates: Treat future release-preflight smoke failures on hidden
  CLI flags as installer-template compatibility regressions first.

- Related Incidents/Bugs:
  [2026-04-07-hosted-installer-upgrades-runtime-without-advancing-repo-pin.md](2026-04-07-hosted-installer-upgrades-runtime-without-advancing-repo-pin.md)

- Version/Build: canonical `main` at `v0.1.10` preflight, before dispatch.

- Customer Comms: internal maintainer-only release-lane hosted-installer fix.

- Code References: release asset publisher, local release smoke harness,
  `tests/unit/install/test_release_bootstrap.py`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Fix Commit/PR: current branch `2026/freedom/v0.1.10-align-pin-compat`,
  pending commit/push.
