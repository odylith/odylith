- Bug ID: CB-007

- Status: Open

- Created: 2026-03-28

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The generated installer's inline release-validation script
  over-escaped the Odylith wheel regex. It looked for filenames matching a
  literal backslash before `.whl`, so it rejected a correct release manifest
  that exposed exactly one real Odylith wheel asset.

- Impact: Local hosted-asset smoke failed during release validation after
  signature checks, even though the generated manifest and wheel asset were
  correct.

- Components Affected: hosted installer validator, release manifest proof
  contract, local maintainer release smoke.

- Environment(s): local hosted-asset rehearsal against generated release
  assets.

- Root Cause: The inline Python validator emitted `.*\\\\.whl` inside a raw
  regex string where `.*\\.whl` was required.

- Solution: Emit the wheel-match regex with a single escaped dot in the
  generated validator and pin that exact expression in unit tests.

- Verification: The generated installer script now contains the corrected wheel
  regex. Local hosted-asset smoke remains the final operational close
  condition.

- Prevention: Keep generated-installer tests focused on the exact wheel-regex
  line so code-generation escaping errors fail locally before maintainer smoke.

- Detected By: Local hosted-asset smoke during maintainer relaunch proof.

- Failure Signature: `release manifest must contain exactly one Odylith wheel
  asset` even though the manifest exposes one valid Odylith wheel.

- Trigger Path: Hosted installer release validation.

- Ownership: Hosted installer contract and release manifest validation logic.

- Timeline: The new local hosted-asset proof progressed past URL handling and
  then surfaced that the generated validator no longer matched the release
  wheel it was meant to prove.

- Blast Radius: Maintainer local hosted-asset proof. A published installer
  would have rejected valid manifests until this was fixed.

- SLO/SLA Impact: Installer credibility and pre-dispatch proof both fail even
  when release assets are correct.

- Data Risk: None.

- Security/Compliance: The fix preserves strict manifest validation; it only
  corrects the wheel-match expression.

- Invariant Violated: A valid release manifest with exactly one Odylith wheel
  must pass installer-side validation.

- Workaround: none.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not weaken the wheel-asset contract; fix the generator
  instead of loosening the validator.

- Preflight Checks: Review this bug and the Release component spec before
  changing installer-side manifest validation again.

- Regression Tests Added: `tests/unit/install/test_release_bootstrap.py`

- Monitoring Updates: none.

- Related Incidents/Bugs: `2026-03-28-local-release-smoke-installer-rejects-localhost-assets-with-port.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: none.

- Customer Comms: none.

- Code References: hosted installer generator

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: Pending.
