- Bug ID: CB-064

- Status: Open

- Created: 2026-04-07

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Running the hosted installer in an already-installed consumer
  repo can activate a newer verified runtime while leaving
  `odylith/runtime/source/product-version.v1.json` pinned to the older version.
  The repo lands in `diverged_verified_version` until the operator runs an
  explicit `odylith upgrade --to X.Y.Z --write-pin`.

- Impact: The public “latest and greatest” installer path can leave consumers in
  a confusing split state: `Active` is newer, `Pinned` is older, and `version`
  plus `doctor` read like the repo still needs one more lifecycle command after
  a supposedly successful hosted install.

- Components Affected: hosted installer generation in
  `scripts/release/publish_release_assets.py`, install CLI flow in
  `src/odylith/cli.py`, install manager pin-alignment semantics in
  `src/odylith/install/manager.py`, public install and upgrade guidance.

- Environment(s): Consumer repos with an existing Odylith install upgraded via
  `curl -fsSL https://odylith.ai/install.sh | bash`.

- Root Cause: The hosted installer ends by calling
  `odylith install --repo-root . --version <release>` which stages and activates
  the requested runtime but intentionally preserves an existing repo pin. That
  behavior is fine for plain rematerialization, but it is a mismatch for the
  public hosted-installer upgrade path.

- Solution: Give the hosted installer an explicit pin-alignment path for
  existing installs so the final active runtime and tracked repo pin converge in
  one command, and print an explicit repo-pin outcome line at closeout.

- Verification: Hosted-installer generation tests and install-manager or CLI
  tests should prove existing installs upgraded through the hosted path finish
  with matching active and pinned versions.

- Prevention: Public bootstrap and upgrade entrypoints should not leave
  consumers in a split-brain active-versus-pinned posture unless the terminal
  explicitly says that was intentional.

- Detected By: Real downstream consumer upgrade from `0.1.7` to `0.1.9` on
  2026-04-07 via the hosted installer.

- Failure Signature: Final posture shows `Active: <new>` and `Pinned: <old>`
  until the operator manually runs `odylith upgrade --to <new> --write-pin`.

- Trigger Path: Hosted installer closeout on an already-installed consumer repo.

- Ownership: hosted install contract and install/upgrade pin semantics.

- Timeline: Earlier install hardening separated bootstrap, upgrade, and
  reinstall semantics correctly for the CLI, but the hosted installer still
  closes out through the rematerialize path instead of the converge-active-plus-pin path.

- Blast Radius: Public installer trust, upgrade clarity, and operator time spent
  running a second lifecycle command after a successful hosted install.

- SLO/SLA Impact: Medium operator-trust and workflow-friction impact.

- Data Risk: Low.

- Security/Compliance: No direct security issue; this is a lifecycle contract
  mismatch.

- Invariant Violated: The hosted installer should leave an already-installed
  consumer repo on one clear truthful posture, not a silent active-versus-pin
  divergence.

- Workaround: Run `./.odylith/bin/odylith upgrade --repo-root . --to X.Y.Z --write-pin`
  after the hosted installer.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Keep direct CLI install semantics explicit; only the hosted
  installer or an explicit install flag should auto-align an existing repo pin.

- Preflight Checks: Inspect install, upgrade, reinstall, hosted installer
  template, and current repo-pin messaging before changing the public bootstrap
  closeout.

- Regression Tests Added:
  `tests/unit/install/test_release_bootstrap.py`,
  `tests/unit/test_cli.py`,
  `tests/integration/install/test_manager.py`

- Monitoring Updates: Watch hosted installer closeouts for any remaining
  `diverged_verified_version` posture when the installer just activated a newer
  runtime.

- Residual Risk: Older consumer repos with missing pins may still need the
  repair path instead of normal hosted-install convergence.

- Related Incidents/Bugs:
  [CB-003](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md),
  [CB-063](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-07-runtime-retention-prune-fails-on-read-only-stale-runtime-trees.md)

- Version/Build: Odylith `0.1.9` observed on 2026-04-07 during downstream
  hosted-install upgrade from `0.1.7`.

- Config/Flags: Default hosted installer path.

- Customer Comms: The installer really did upgrade the runtime, but it left the
  repo pin behind. The fix makes the hosted path converge both in one go and
  say so plainly.

- Code References: `scripts/release/publish_release_assets.py`,
  `src/odylith/cli.py`, `src/odylith/install/manager.py`,
  `tests/unit/install/test_release_bootstrap.py`, `tests/unit/test_cli.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Fix Commit/PR: Pending.
