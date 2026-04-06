- Bug ID: CB-006

- Status: Open

- Created: 2026-03-28

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The generated installer validated the release and unpacked the
  bootstrap runtime, but then attempted to move the runtime into
  `.odylith/runtime/versions/<version>` before ensuring that the `versions/`
  directory existed.

- Impact: Local hosted-asset smoke failed during runtime activation even
  though asset fetch, signature proof, and manifest validation all succeeded.

- Components Affected: hosted installer activation path, local maintainer
  release smoke.

- Environment(s): local hosted-asset rehearsal against generated install
  scripts.

- Root Cause: The shell bootstrap created `.odylith/runtime/` and
  `.odylith/bin/`, but not `.odylith/runtime/versions/`.

- Solution: Create `.odylith/runtime/versions/` before moving the validated
  runtime into place.

- Verification: The generated installer now emits the corrected `mkdir -p`
  line and local hosted-asset smoke remains the final operational close
  condition.

- Prevention: Keep generated-installer tests checking the activation-directory
  setup step explicitly.

- Detected By: Local hosted-asset smoke during maintainer relaunch proof.

- Failure Signature: `mv: .../.odylith/runtime/versions/<version>: No such file
  or directory` during installer activation.

- Trigger Path: Hosted installer activation after manifest validation.

- Ownership: Hosted installer contract and local maintainer release proof
  lane.

- Timeline: The deeper hosted-asset rehearsal advanced past fetch and
  validation, then exposed that the generated installer still missed one
  runtime activation directory.

- Blast Radius: Maintainer local hosted-asset proof. A published installer
  would have failed at first activation until this was fixed.

- SLO/SLA Impact: First-install robustness degrades even when release assets
  are valid.

- Data Risk: None.

- Security/Compliance: None beyond preserving the already-validated runtime
  activation contract.

- Invariant Violated: The installer must create every runtime activation path
  it needs before moving a validated runtime into place.

- Workaround: none.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not bypass the managed runtime activation layout just to
  make rehearsal pass.

- Preflight Checks: Review this bug and the Install/Upgrade runbook before
  changing installer activation steps again.

- Regression Tests Added: `tests/unit/install/test_release_bootstrap.py`

- Monitoring Updates: none.

- Related Incidents/Bugs: `2026-03-28-generated-installer-validator-over-escapes-wheel-regex.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: none.

- Customer Comms: none.

- Code References: hosted installer generator

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
