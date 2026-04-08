- Bug ID: CB-061

- Status: Closed

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

- Solution: Hosted install and repair now classify allowlisted benign
  verifier chatter separately from fatal stderr. Successful verification keeps
  one explicit success line, filters the known offline-mode and unsupported
  key-type warning spill from the happy path, and still preserves fatal stderr
  when verification actually fails.

- Verification: Fixed on 2026-04-08. `PYTHONPATH=src python3 -m pytest -q
  tests/unit/install/test_release_assets.py tests/unit/install/test_release_bootstrap.py
  tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py
  tests/unit/runtime/test_backfill_workstream_traceability.py
  tests/unit/runtime/test_delivery_intelligence_engine.py
  tests/unit/runtime/test_validate_component_registry_contract.py
  tests/integration/install/test_manager.py::test_install_bundle_align_pin_advances_existing_repo_pin_to_active_runtime
  tests/integration/install/test_manager.py::test_upgrade_prunes_runtime_and_release_cache_retention
  tests/integration/install/test_manager.py::test_upgrade_warns_and_continues_when_retention_prune_stays_permission_denied`
  passed with `176 passed in 1.75s`, covering the release-asset and CLI
  verification messaging path alongside the adjacent hosted-install fixes.

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

- Regression Tests Added:
  `tests/unit/install/test_release_assets.py`,
  `tests/unit/test_cli.py`

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

- Fix Commit/PR: `2026/freedom/v0.1.10` release-hardening closeout series.
