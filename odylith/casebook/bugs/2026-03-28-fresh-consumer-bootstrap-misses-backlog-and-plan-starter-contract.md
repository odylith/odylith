- Bug ID: CB-004

- Status: Open

- Created: 2026-03-28

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: Hosted consumer rehearsal for the abandoned Odylith `v0.1.2`
  prelaunch drill failed after successful install, upgrade, rollback, and
  re-upgrade because a fresh consumer repo bootstrap did not include the
  minimal tracked backlog and plan source artifacts required for `odylith sync`.

- Impact: A first-time supported consumer install can complete and still fail
  on the first `odylith sync`, leaving the repo in an immediately broken
  governed state until the maintainer manually creates missing
  `odylith/radar/source` and `odylith/technical-plans` starter artifacts.

- Components Affected: `src/odylith/install/manager.py`, consumer starter
  bootstrap contract, maintainer rehearsal lane, `bin/consumer-rehearsal`,
  backlog and plan starter indexes.

- Environment(s): hosted prelaunch consumer rehearsal on macOS (Apple
  Silicon), hosted `v0.1.2` install and upgrade path into a fresh disposable
  repo with no preexisting Odylith governance truth.

- Root Cause: First install created the top-level customer-owned `odylith/`
  tree and runtime pin files, but it did not create the empty
  `odylith/radar/source/ideas/` root, `odylith/radar/source/INDEX.md`, or
  `odylith/technical-plans/INDEX.md` that `odylith sync` and the backlog/plan
  validators treat as mandatory starter truth.

- Solution: Expand the first-install customer bootstrap so it creates the empty
  `ideas/` root plus contract-valid empty backlog and plan index files, while
  continuing to preserve any existing customer-owned truth and avoiding
  creation of product-owned Registry or Atlas truth in consumer repos.

- Verification: Source fix and focused regression coverage are landed locally in
  `tests/integration/install/test_manager.py`. The bug remains open until the
  restarted preview line proves that `make consumer-rehearsal` succeeds from
  hosted assets after first install.

- Prevention: Treat first install as a complete starter-truth contract, not
  only a directory scaffold. Consumer rehearsal must continue proving the
  `install -> version -> doctor -> sync` path on a fresh repo.

- Detected By: Hosted prelaunch consumer rehearsal against the abandoned
  `v0.1.2` drill assets.

- Failure Signature: `backlog contract validation FAILED` with missing
  `odylith/radar/source/ideas`, missing backlog index, and missing plan index.

- Trigger Path: `make consumer-rehearsal VERSION=0.1.2 PREVIOUS_VERSION=0.1.0`

- Ownership: Consumer starter bootstrap and governed-surface readiness.

- Timeline: The abandoned `v0.1.2` prelaunch drill restored the
  managed-runtime upgrade and legacy rollback proof, but hosted rehearsal then
  failed later on the first governed `sync` because the fresh consumer starter
  tree was still incomplete.

- Blast Radius: Any first-time supported consumer repo that runs `odylith sync`
  after install or upgrade without manually creating the missing starter truth.

- SLO/SLA Impact: Preview onboarding and proof credibility remain incomplete
  until the starter tree is complete on first install for the restarted line.

- Data Risk: None.

- Security/Compliance: The failure is operational, not a direct security issue,
  but an incomplete starter contract undermines deterministic product behavior.
  The forward fix must keep consumer-owned truth minimal and must not start
  copying Odylith product-truth files into consumer repos.

- Invariant Violated: A successful fresh Odylith install on a supported
  platform must leave the consumer repo able to run `odylith sync` without
  manual scaffolding.

- Workaround: Manually create `odylith/radar/source/ideas/`,
  `odylith/radar/source/INDEX.md`, and `odylith/technical-plans/INDEX.md`
  before running `odylith sync`. This is not acceptable as the product
  contract.

- Rollback/Forward Fix: Forward fix in the restarted preview release.

- Agent Guardrails: Do not expand consumer bootstrap into a copy of Odylith's
  product repo truth. Seed only the minimum empty customer-owned backlog and
  plan starter artifacts required by the governed surface contracts.

- Preflight Checks: Inspect this bug, the active B-005 plan, and the first
  install bootstrap code before touching consumer bootstrap behavior.

- Regression Tests Added: `tests/integration/install/test_manager.py`.

- Monitoring Updates: Consumer rehearsal should continue validating the fresh
  install `sync` path explicitly, not just install/upgrade/rollback.

- Related Incidents/Bugs:
  `2026-03-28-public-consumer-install-depends-on-machine-python.md`,
  `2026-03-28-public-consumer-rollback-to-legacy-preview-runtime-fails.md`

- Version/Build: Abandoned prelaunch `v0.1.2` drill assets.

- Config/Flags:
  `make consumer-rehearsal VERSION=0.1.2 PREVIOUS_VERSION=0.1.0`

- Customer Comms: No canonical public release should claim first-install proof
  until the starter governance truth is complete and first install is
  immediately sync-capable.

- Code References: `src/odylith/install/manager.py`,
  `tests/integration/install/test_manager.py`, `bin/consumer-rehearsal`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
