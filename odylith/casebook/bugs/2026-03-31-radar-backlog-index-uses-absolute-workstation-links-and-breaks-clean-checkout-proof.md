- Bug ID: CB-024

- Status: Closed

- Created: 2026-03-31

- Fixed: 2026-03-31

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: `odylith/radar/source/INDEX.md` had drifted to absolute
  workstation file links under `/Users/freedom/code/odylith/...` instead of
  repo-relative backlog links. Clean GitHub Actions checkouts could therefore
  fail release proof even when the workstream data itself was correct.

- Impact: Maintainer `candidate-proof` failed in CI with backlog link
  portability errors, blocking PR #24 from merging and delaying the `v0.1.6`
  release lane.

- Components Affected: `odylith/radar/source/INDEX.md`,
  `src/odylith/runtime/governance/backlog_authoring.py`,
  `src/odylith/runtime/governance/reconcile_plan_workstream_binding.py`,
  `src/odylith/runtime/governance/validate_backlog_contract.py`,
  backlog portability hygiene coverage.

- Environment(s): Odylith product repo maintainer checkout, especially clean
  GitHub Actions runners validating backlog governance from a fresh clone.

- Root Cause: The backlog write paths were still emitting absolute resolved
  paths for workstream links, while the validator and clean-checkout proof
  needed portable repo-relative links. That drift left the committed Radar
  index machine-specific.

- Solution: Make backlog link generation canonicalize to repo-relative
  `odylith/radar/source/ideas/...` targets, preserve validator tolerance for
  rebased legacy absolute links, and rewrite the committed Radar index to the
  portable form.

- Verification: Focused backlog authoring, reconcile, backlog contract, install
  repair, and hygiene suites pass locally, and the real repo backlog contract
  validates cleanly after the index rewrite.

- Prevention: Treat repo-relative backlog links as the only canonical contract.
  Keep a hygiene assertion over the committed Radar index so workstation paths
  cannot creep back in silently.

- Detected By: GitHub Actions `candidate-proof` on PR #24 after the
  `AGENTS.md` repair drift was already fixed.

- Failure Signature: `odylith/radar/source/INDEX.md: link for B-### must
  resolve under repo root` and `link target mismatch` errors on the GitHub
  runner because the index still pointed at `/Users/freedom/...`.

- Trigger Path: Clean-checkout release-candidate validation reading
  `odylith/radar/source/INDEX.md` during backlog governance proof.

- Ownership: Release hardening, backlog governance portability, and Radar
  source integrity.

- Timeline: The absolute-link drift survived because backlog authoring and
  successor-binding paths kept resolving paths eagerly, while most local work
  happened in the same canonical checkout where those links still looked valid.

- Blast Radius: Maintainer CI, any cloned checkout validating backlog truth,
  and future release lanes that depend on portable governance artifacts.

- SLO/SLA Impact: Release-candidate reliability degrades and maintainers lose
  time chasing false portability failures instead of real release blockers.

- Data Risk: None.

- Security/Compliance: None.

- Invariant Violated: Maintained Odylith governance artifacts must remain
  portable across machines and clean checkouts.

- Workaround: Manually rewrite the committed Radar index links before running
  proof. This is not acceptable as the durable contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not fix this only in the validator. The committed Radar
  index and the backlog write paths must both move back to portable repo-root
  links.

- Preflight Checks: Inspect this bug, `odylith/radar/source/INDEX.md`, and the
  backlog governance writers before changing backlog link behavior again.

- Regression Tests Added: `tests/unit/runtime/test_backlog_authoring.py`,
  `tests/unit/runtime/test_validate_backlog_contract.py`,
  `tests/unit/runtime/test_reconcile_plan_workstream_binding.py`,
  `tests/unit/runtime/test_hygiene.py`

- Monitoring Updates: None.

- Related Incidents/Bugs:
  `2026-03-31-product-repo-doctor-repair-rewrites-root-agents-to-stale-managed-block.md`

- Version/Build: `v0.1.6` release-candidate hardening.

- Config/Flags: `make release-candidate`, `odylith/radar/source/INDEX.md`
  governance proof.

- Customer Comms: None. This is a maintainer-lane governance portability
  failure.

- Code References: `odylith/radar/source/INDEX.md`,
  `src/odylith/runtime/governance/backlog_authoring.py`,
  `src/odylith/runtime/governance/reconcile_plan_workstream_binding.py`,
  `src/odylith/runtime/governance/validate_backlog_contract.py`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: PR #24, follow-up portability patch pending final merge.
