- Bug ID: CB-076

- Status: Closed

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
  emitted wrapped successful verifier stderr before the `OK:` lines. The
  benign warning allowlist in `release_assets.py` checked one stderr line at a
  time, so `Failed to load a trusted root key: unsupported ...` on one line
  and `key type: 7` on the next line escaped suppression even though the whole
  warning block was already classified as non-fatal.

- Solution: Fold wrapped Sigstore stderr continuations into one warning chunk
  before allowlist matching, then keep suppressing only the known non-fatal
  trust bootstrap warnings while preserving any unexpected or fatal verifier
  stderr.

- Verification: Fixed on 2026-04-10 with focused install-verification proof in
  `tests/unit/install/test_release_assets.py`, including the real wrapped
  warning shape from `trust.py` and a mixed benign-plus-unexpected-warning
  case to prove only allowlisted chatter is suppressed.

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

- Regression Tests Added: `tests/unit/install/test_release_assets.py` now
  proves both the wrapped `unsupported ... key type: 7` warning suppression
  path and the preservation of unexpected verifier warnings alongside the same
  benign wrapped warning.

- Monitoring Updates: Watch `dogfood-activate`, consumer rehearsal, and GA gate
  logs for any reappearance of wrapped trust-root warnings such as
  `unsupported ... key type: 7` after successful verification.

- Residual Risk: Low. The remaining risk is future benign-warning shape drift
  in Sigstore/TUF output; unexpected stderr still prints in full.

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

- Fix Commit/PR: Pending local branch integration.
