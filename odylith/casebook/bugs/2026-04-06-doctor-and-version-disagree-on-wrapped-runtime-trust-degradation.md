- Bug ID: CB-056

- Status: Open

- Created: 2026-04-06

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: After workaround cleanup, `odylith doctor` can report a healthy
  install while `odylith version` still shows `Runtime source: wrapped_runtime`
  with only a generic fallback explanation. The two commands do not tell a
  coherent trust story.

- Impact: Operators can misread a trust-degraded wrapped runtime as equivalent
  to a pinned verified runtime and make the wrong release or maintenance
  decision.

- Components Affected: `src/odylith/install/manager.py`,
  `src/odylith/cli.py`, runtime-source derivation, self-host posture
  validation.

- Environment(s): Product repo and consumer repos where runtime trust is
  degraded but execution still works.

- Root Cause: Runtime-source classification relies too heavily on install-state
  metadata, while doctor-health messaging and version-status explanation are
  derived separately.

- Solution: Move runtime-source classification and trust-degradation reason
  derivation behind one shared helper, then make both `doctor` and `version`
  explain wrapped-runtime posture consistently.

- Verification: CLI and posture-validation tests should prove the same runtime
  state produces aligned `doctor` and `version` output.

- Prevention: Status derivation for trust-sensitive lanes should have one
  authoritative code path, not parallel output logic.

- Detected By: Manual downstream migration review on 2026-04-06.

- Failure Signature: `doctor` reports healthy while `version` shows
  `Runtime source: wrapped_runtime`.

- Trigger Path: `odylith doctor --repo-root .` and
  `odylith version --repo-root .`

- Ownership: runtime-status and lane-introspection contract.

- Timeline: Earlier lane-introspection work made runtime posture visible, but
  the wrapped-runtime degraded case still has split reasoning paths.

- Blast Radius: Operator status reads, release eligibility judgment, and trust
  in Odylith’s own lane reporting.

- SLO/SLA Impact: Medium operator-trust impact.

- Data Risk: Low.

- Security/Compliance: Indirect trust-posture clarity impact.

- Invariant Violated: `doctor` and `version` should describe the same live
  runtime trust posture.

- Workaround: Infer the real state manually from both commands and runtime
  files, which defeats the point of the supported status surface.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Do not add status labels that weaken the existing pinned
  versus source-local lane model.

- Preflight Checks: Inspect runtime-source derivation, release-eligible logic,
  and wrapped-runtime tests before adding a new explanation path.

- Regression Tests Added: Pending.

- Monitoring Updates: Watch for healthy doctor output paired with non-pinned
  runtime source in product-repo posture checks.

- Residual Risk: Additional runtime-source subtypes may still be needed later
  if more degraded states become operator-visible.

- Related Incidents/Bugs:
  [CB-023](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-31-product-repo-doctor-repair-rewrites-root-agents-to-stale-managed-block.md),
  [CB-026](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md)

- Version/Build: Odylith 0.1.7 observed on 2026-04-06 during downstream
  migration analysis.

- Config/Flags: Default status and doctor commands.

- Customer Comms: Odylith’s status surfaces could describe a runnable runtime
  more optimistically than its trust posture deserved; the fix makes the
  wrapped-runtime story explicit and consistent.

- Code References: `src/odylith/install/manager.py`, `src/odylith/cli.py`,
  `tests/unit/runtime/test_validate_self_host_posture.py`,
  `tests/unit/test_cli.py`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
