- Bug ID: CB-008

- Status: Open

- Created: 2026-03-28

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The GitHub test workflow still booted the repo with direct
  `pip install -e . pytest` commands even after the relaunch moved Odylith's
  canonical maintainer build path onto Hatch.

- Impact: CI exercised a different environment-management path from the
  canonical maintainer lane, which weakened the repo's Hatch-first build
  posture and made it easier for test-only environment drift to slip past
  local and release validation.

- Components Affected: `.github/workflows/test.yml`, Hatch environment
  contract, repo CI posture.

- Environment(s): GitHub Actions `test` workflow on pushes and pull requests.

- Root Cause: The relaunch work updated release preflight and release publish
  flows to use Hatch, but the generic test workflow still used the older
  direct-pip bootstrap path.

- Solution: Bootstrap Hatch in CI, create the managed Hatch environment, and
  run the test suite through `hatch run pytest -q` so repo validation uses the
  same environment frontend as the canonical maintainer lane.

- Verification: The GitHub test workflow now creates the Hatch environment and
  executes pytest through Hatch.

- Prevention: Keep operator-facing and maintainer-facing build/test workflows
  aligned on one canonical frontend instead of letting CI, local validation,
  and release proof diverge.

- Detected By: Hatch posture sweep during relaunch implementation on
  `2026/freedom/release-reset-runtime-footprint`.

- Failure Signature: `.github/workflows/test.yml` contained
  `python -m pip install -e . pytest` followed by direct `pytest -q`.

- Trigger Path: Any push or pull request that ran the GitHub `test` workflow.

- Ownership: Repo CI and build-environment contract.

- Timeline: The release lane was corrected first, which exposed the remaining
  CI workflow drift during final relaunch verification.

- Blast Radius: All CI test runs for the public repo.

- SLO/SLA Impact: Build/test reproducibility risk; no direct customer outage.

- Data Risk: None.

- Security/Compliance: Lower consistency between tested and released build
  environments increases validation ambiguity.

- Invariant Violated: Odylith should be Hatch-based for repo build/test
  execution rather than relying on ad hoc direct-pip runs.

- Workaround: None needed after the forward fix. Before the fix, local Hatch
  validation remained the closest trustworthy signal.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not reintroduce direct `pip install -e . pytest` into
  repo CI unless Odylith's canonical build frontend changes intentionally.

- Preflight Checks: Inspect the active relaunch plan, Release component spec,
  and repo workflows before changing build/test entrypoints again.

- Regression Tests Added: None. Workflow diff only.

- Monitoring Updates: None.

- Related Incidents/Bugs: `2026-03-28-full-stack-managed-runtime-payloads-are-too-large-for-install-and-upgrade.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: GitHub Actions `test` workflow.

- Customer Comms: None.

- Code References: `.github/workflows/test.yml`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03-28-odylith-managed-runtime-bundles-and-supported-platform-contract.md`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: Pending.
