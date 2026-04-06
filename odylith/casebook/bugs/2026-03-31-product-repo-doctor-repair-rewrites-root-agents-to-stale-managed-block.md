- Bug ID: CB-023

- Status: Open

- Created: 2026-03-31

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: In the Odylith product repo, `odylith doctor --repair` could
  rewrite the tracked root `AGENTS.md` scope block back to stale generated
  guidance, leaving the worktree dirty even when the repair path was otherwise
  healthy.

- Impact: Maintainer proof lanes that correctly require a clean worktree could
  fail for a stale-guidance reason. In practice this broke the GitHub
  `candidate-proof` lane because the workflow repaired the repo-local runtime
  and then hit `release lane requires a clean worktree`.

- Components Affected: `src/odylith/install/agents.py`,
  `src/odylith/install/manager.py`, root `AGENTS.md`, maintainer
  `release-candidate` workflow, product-repo repair contract.

- Environment(s): Odylith product repo maintainer checkout or clean GitHub
  Actions checkout running `odylith doctor --repair` before release proof.

- Root Cause: The generated product-repo managed scope block in
  `src/odylith/install/agents.py` had drifted from the tracked root
  `AGENTS.md` source truth. `update_agents_file(...)` therefore treated the
  healthy product repo as stale and rewrote the file during repair.

- Solution: Keep product-repo repair non-mutating by syncing the generated
  product scope block to the tracked root `AGENTS.md` contract, then add
  regressions that compare the generator output against the live repo root and
  exercise `doctor_bundle(..., repair=True)` with the real product-repo
  guidance text.

- Verification: the source-local Odylith doctor repair path now leaves the
  product repo clean, and targeted regressions covering the generator plus
  product-repo repair replay pass locally. GitHub `candidate-proof` rerun is
  still pending before closure.

- Prevention: Treat the tracked root `AGENTS.md` scope block as authoritative
  for product-repo repair. Any future change to that block must update the
  generator and the regression that compares them directly.

- Detected By: GitHub Actions `release-candidate` workflow on PR #24 after
  local release-candidate proof had already passed from a clean branch.

- Failure Signature: `make release-candidate` exited with
  `error: release lane requires a clean worktree` immediately after `doctor
  --repair`, while `make lane-show` reported `clean_worktree: no`.

- Trigger Path: `.github/workflows/release-candidate.yml` running the
  source-local Odylith doctor repair step in a clean checkout before
  `make release-candidate`.

- Ownership: Release hardening and product-repo install/repair contract.

- Timeline: The release-hardening stream already required product-repo repair
  to be idempotent, but this legacy generated-scope drift survived because the
  existing tests seeded generic repo-root guidance instead of the live tracked
  root `AGENTS.md`.

- Blast Radius: Maintainer CI, local maintainer repair flows, and any product
  checkout relying on `doctor --repair` before proof.

- SLO/SLA Impact: Release-candidate reliability degrades and maintainers lose
  time chasing false dirty-worktree failures.

- Data Risk: None.

- Security/Compliance: None.

- Invariant Violated: Product-repo repair and dogfood flows must be rerunnable
  without leaving tracked guidance drift behind.

- Workaround: Manually restore `AGENTS.md` after repair or skip the repair
  step. Neither is acceptable as the long-term contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not paper over this with workflow-only cleanup if the
  underlying product generator remains stale. The product repair path itself
  must preserve tracked source truth.

- Preflight Checks: Inspect this bug, the active B-033 plan, and the install
  manager or release-candidate workflow before changing product-repo repair
  behavior again.

- Regression Tests Added: `tests/unit/install/test_agents.py`,
  `tests/integration/install/test_manager.py`

- Monitoring Updates: None.

- Related Incidents/Bugs:
  `2026-03-28-release-preflight-fails-when-dist-contains-stale-wheel.md`,
  `2026-03-29-release-auto-tagging-burns-unpublished-patch-versions-and-skips-ga-candidates.md`

- Version/Build: `v0.1.6` release-candidate hardening.

- Config/Flags: `odylith doctor --repo-root . --repair`,
  `make release-candidate`.

- Customer Comms: None. This is a maintainer-lane integrity failure.

- Code References: `src/odylith/install/agents.py`,
  `src/odylith/install/manager.py`,
  `.github/workflows/release-candidate.yml`,
  `AGENTS.md`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: Pending.
