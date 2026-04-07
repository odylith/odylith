- Bug ID: CB-061

- Status: Open

- Created: 2026-04-06

- Severity: P1

- Reproducibility: Medium

- Type: Product

- Description: Successful Sigstore/TUF verification during install or repair
  can still print scary non-fatal warnings such as offline-mode or unsupported
  key-type chatter, without one explicit success line making it clear that
  verification actually passed.

- Impact: Operators can walk away from a successful verified install thinking
  the trust bootstrap may have partially failed.

- Components Affected: `src/odylith/install/release_assets.py`,
  `src/odylith/cli.py`, install and repair success messaging, release-note copy.

- Environment(s): Install or repair flows that invoke external verifier tools
  and receive benign stderr warnings on successful verification.

- Root Cause: Successful verifier stderr is surfaced too literally and not
  classified into fatal-versus-benign output paths.

- Solution: Capture verifier stderr, suppress or translate only allowlisted
  benign warnings on success, keep fatal details intact on failure, and print
  one explicit verification-success line.

- Verification: Release-asset and CLI tests should prove success-path warning
  suppression and failure-path stderr preservation.

- Prevention: Security messaging should differentiate successful strict
  verification from real verifier failure instead of printing both as equally
  scary terminal output.

- Detected By: Real downstream migration review on 2026-04-06.

- Failure Signature: Scary warning block during successful verification with no
  explicit “verification succeeded” summary line.

- Trigger Path: release-asset verification during install, reinstall, and
  repair.

- Ownership: supply-chain verification output contract.

- Timeline: The runtime trust wave strengthened fail-closed verification, but
  the success-path messaging stayed too raw.

- Blast Radius: Install trust perception, repair confidence, and release-note
  credibility.

- SLO/SLA Impact: Medium operator-trust impact.

- Data Risk: Low.

- Security/Compliance: Security-communication clarity issue; verification still
  succeeds.

- Invariant Violated: Successful strict verification should be clearly
  recognizable as success.

- Workaround: Inspect return codes or ignore the warnings manually.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Suppress only explicitly allowlisted benign warnings and
  never hide fatal verifier stderr.

- Preflight Checks: Inspect verifier subprocess handling and current stderr
  payloads before designing the allowlist.

- Regression Tests Added: Pending.

- Monitoring Updates: Watch install and repair logs for allowlisted benign
  warning classes after the success-path cleanup lands.

- Residual Risk: Additional benign warning variants may still need explicit
  classification later.

- Related Incidents/Bugs:
  [CB-026](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md)

- Version/Build: Odylith 0.1.7 observed on 2026-04-06 during downstream
  migration.

- Config/Flags: Default verification path.

- Customer Comms: Verification was succeeding more often than the terminal made
  it sound. The fix keeps strict verification while making the successful path
  clearly readable.

- Code References: `src/odylith/install/release_assets.py`,
  `src/odylith/cli.py`, `tests/unit/install/test_release_assets.py`,
  `tests/unit/test_cli.py`

- Runbook References: `odylith/SECURITY_POSTURE.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
