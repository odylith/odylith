- Bug ID: CB-054

- Status: Open

- Created: 2026-04-06

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: On macOS, Odylith can treat Finder metadata such as
  `.DS_Store` or AppleDouble `._*` files inside
  `.odylith/runtime/versions/<version>/` as fatal managed-runtime integrity
  drift, which blocks trusted runtime reuse and feature-pack application even
  though the runtime bytes themselves are unchanged.

- Impact: Install, reinstall, repair, and feature-pack activation can strand a
  healthy runtime on a common platform-specific noise case. Operators see a
  trust failure for a runtime Odylith just staged successfully.

- Components Affected: `src/odylith/install/runtime_integrity.py`,
  `src/odylith/install/runtime.py`, managed runtime trust policy, feature-pack
  preflight.

- Environment(s): macOS Apple Silicon and other Finder-touched worktrees with
  managed runtimes under `.odylith/runtime/versions/`.

- Root Cause: Runtime tree-manifest generation and verification treat every
  unexpected filesystem entry as meaningful drift. There is no narrow policy
  exception for known OS metadata noise.

- Solution: Add a runtime-tree policy helper that ignores only `.DS_Store` and
  AppleDouble `._*` during manifest generation, integrity verification, and
  target-version residue cleanup. Keep other unexpected entries fatal.

- Verification: Unit tests should prove `.DS_Store` and `._*` do not fail
  trust validation while arbitrary unexpected files still do.

- Prevention: Trust policy needs an explicit platform-noise allowlist instead
  of assuming every runtime tree entry is stable across local OS behavior.

- Detected By: Real downstream migration rehearsal on 2026-04-06 during
  Odylith 0.1.7 macOS Apple Silicon install and repair.

- Failure Signature: `feature packs can only be applied to a trusted Odylith
  runtime: managed runtime tree entry unexpected: .../.DS_Store`

- Trigger Path: managed runtime tree verification during feature-pack
  activation and repair health checks.

- Ownership: managed runtime trust boundary and install lifecycle.

- Timeline: The stricter runtime trust wave closed mutable-runtime gaps, but it
  did not account for common macOS metadata files that can appear inside a
  staged runtime tree.

- Blast Radius: macOS install and repair reliability, trust posture, and
  operator confidence in runtime integrity output.

- SLO/SLA Impact: Medium operator-blocking release-lifecycle impact.

- Data Risk: Low.

- Security/Compliance: Security-positive intent, but currently over-fails on
  benign platform noise.

- Invariant Violated: Known OS metadata noise must not be indistinguishable
  from real runtime tamper.

- Workaround: Manually delete `.DS_Store` and retry, which is not an acceptable
  supported repair path.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Do not ignore arbitrary dotfiles or widen the trust
  allowlist beyond explicit macOS metadata noise.

- Preflight Checks: Inspect runtime tree enumeration, trust-manifest writes,
  and feature-pack preflight before widening the entry filter.

- Regression Tests Added: Pending.

- Monitoring Updates: Watch macOS repair and feature-pack failures for trust
  drift now attributable only to non-allowlisted entries.

- Residual Risk: Other OS-specific metadata could still need explicit policy
  later.

- Related Incidents/Bugs:
  [CB-003](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md),
  [CB-015](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-release-download-cache-and-runtime-restage-lose-atomicity-on-failure.md),
  [CB-026](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md)

- Version/Build: Odylith 0.1.7 observed on 2026-04-06 during downstream
  migration.

- Config/Flags: Default trust validation and feature-pack activation path.

- Customer Comms: Odylith was over-strict on known macOS metadata noise; the
  fix keeps runtime trust strict on real drift while making the policy
  platform-aware.

- Code References: `src/odylith/install/runtime_integrity.py`,
  `src/odylith/install/runtime.py`, `tests/unit/install/test_runtime.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`,
  `odylith/SECURITY_POSTURE.md`

- Fix Commit/PR: Pending.
