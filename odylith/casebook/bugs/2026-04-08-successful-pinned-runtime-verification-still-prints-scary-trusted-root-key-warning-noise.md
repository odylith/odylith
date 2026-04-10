- Bug ID: CB-076

- Status: Open

- Created: 2026-04-08

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Successful pinned-runtime verification in shipped release-proof
  lanes still prints scary trust-warning noise such as `Failed to load a
  trusted root key: unsupported key type: 7` immediately before `OK:` asset
  verification lines. The hosted installer cleanup landed for `v0.1.10`, but
  dogfood activation, consumer rehearsal, and GA gate can still surface the
  same warning block even when manifest, wheel/runtime, provenance, and SBOM
  verification all actually pass.

- Impact: Maintainers and consumers can read a healthy release verification as
  a partial trust failure. That undercuts supply-chain confidence at exactly
  the moment Odylith is trying to prove a verified release.

- Components Affected: pinned-runtime release verification messaging,
  `src/odylith/install/release_assets.py`, shipped-runtime trust bootstrap
  output, `make dogfood-activate`, `make consumer-rehearsal`,
  `make ga-gate`, release component contract.

- Environment(s): Odylith product repo maintainer mode, pinned dogfood on
  macOS Apple Silicon, canonical `v0.1.10` release and GA proof on 2026-04-08,
  plus consumer rehearsal paths that verify published release assets through
  the managed runtime rather than the hosted `install.sh` wrapper.

- Root Cause: The `v0.1.10` cleanup filtered allowlisted benign verifier noise
  in the hosted installer shell path, but the pinned-runtime proof lanes still
  emit raw successful verifier stderr before the `OK:` lines. The benign
  warning classification is therefore not yet enforced consistently across all
  shipped verification entrypoints.

- Solution: Extend the benign-warning suppression or translation contract to
  the pinned-runtime verification paths used by dogfood activation, consumer
  rehearsal, and GA gate, while preserving fatal verifier stderr and explicit
  success proof for real failures.

- Verification: Re-observed on 2026-04-08 during `make dogfood-activate`,
  `make consumer-rehearsal PREVIOUS_VERSION=0.1.9`, and
  `make ga-gate PREVIOUS_VERSION=0.1.9`, where the warning
  `Failed to load a trusted root key: unsupported key type: 7` appeared
  immediately before `OK:` lines for verified release assets and the release
  lane still completed successfully to GA.

- Prevention: Warning suppression for successful verification is not complete
  until the same calm success contract holds across hosted installer bootstrap,
  pinned dogfood, consumer rehearsal, and GA proof lanes.

- Detected By: Maintainer GA closeout for `v0.1.10` after canonical release
  dispatch succeeded.

- Failure Signature: Successful verification prints one or more scary trust
  warnings such as `unsupported key type: 7` immediately before `OK:` asset
  lines and final successful release proof.

- Trigger Path: `make dogfood-activate`, `make consumer-rehearsal
  PREVIOUS_VERSION=0.1.9`, `make ga-gate PREVIOUS_VERSION=0.1.9`

- Ownership: Release verification messaging, managed-runtime trust bootstrap
  output, release component contract.

- Timeline: `CB-061` closed the hosted installer path for `v0.1.10`, but the
  same warning class remained visible in pinned-runtime proof lanes during the
  final GA run on 2026-04-08.

- Blast Radius: Consumer trust in verified installs, maintainer confidence in
  GA proof output, and the credibility of Odylith's supply-chain story.

- SLO/SLA Impact: No outage; medium trust and operator-confidence regression in
  a release-critical path.

- Data Risk: Low.

- Security/Compliance: Security-communication clarity issue; verification still
  succeeds and remains fail-closed on real errors.

- Invariant Violated: Successful strict verification should read as successful
  across every shipped release-proof lane, not only in one bootstrap wrapper.

- Workaround: If the warning is followed by `OK:` lines for every expected
  asset and the command exits successfully, treat it as benign warning noise.
  Do not treat that workaround as the long-term release contract.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not broaden the allowlist casually. Keep fatal verifier
  stderr intact and prove any suppression in the pinned-runtime lanes that
  actually exercise release and GA proof.

- Preflight Checks: Inspect the successful-verification stderr handling used by
  the managed runtime, then replay dogfood activation and consumer rehearsal
  with real published assets before claiming the noise is fixed.

- Regression Tests Added: None yet. The next release should add direct proof
  for successful pinned-runtime verification output, not just hosted
  install-script filtering.

- Monitoring Updates: Watch `dogfood-activate`, consumer rehearsal, and GA gate
  logs for `unsupported key type: 7` and similar benign verifier chatter after
  the next cleanup lands.

- Residual Risk: Consumers may still be spooked by healthy verification output
  until the pinned-runtime lanes are cleaned up too.

- Related Incidents/Bugs:
  [2026-04-06-successful-trust-bootstrap-still-prints-scary-non-fatal-warnings.md](2026-04-06-successful-trust-bootstrap-still-prints-scary-non-fatal-warnings.md)

- Version/Build: `v0.1.10` GA lane on 2026-04-08.

- Config/Flags: Standard release verification paths, no trust-bypass flags.

- Customer Comms: The published assets verified successfully, but the terminal
  still looked scarier than the truth. Next release should make successful
  verification read as calm success across the full shipped path.

- Code References: `src/odylith/install/release_assets.py`,
  `src/odylith/cli.py`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending next-release release-verification noise cleanup.
