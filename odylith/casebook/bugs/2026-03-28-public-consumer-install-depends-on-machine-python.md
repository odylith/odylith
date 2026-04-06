- Bug ID: CB-013

- Status: Open

- Created: 2026-03-28

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: The first hosted consumer rehearsal for the abandoned Odylith
  `v0.1.0` prelaunch drill failed because the installer still depended on a
  compatible machine Python interpreter instead of an Odylith-managed runtime.

- Impact: The relaunch line cannot treat the abandoned `v0.1.0` drill as a
  valid first-install proof, and install fails outright when compatible Python
  `3.13+` is not already installed on the consumer machine.

- Components Affected: Release installer asset-generation lane,
  `src/odylith/install/runtime.py`, `src/odylith/install/release_assets.py`,
  Release installer contract, maintainer rehearsal lane.

- Environment(s): hosted prelaunch consumer install rehearsal on macOS, first
  install from hosted GitHub release assets, machine default `python3`
  resolving to Python `3.11.2`.

- Root Cause: The hosted installer created both its verification venv and the
  target Odylith runtime from a consumer-machine interpreter instead of
  distributing an Odylith-managed runtime for supported platforms.

- Solution: Publish Odylith-managed runtime bundles for supported macOS and
  Linux platforms and make first install plus upgrade activate those bundles
  directly without depending on a preinstalled consumer-machine Python.
  Strengthen the contract further by pinning the upstream managed-Python
  archive digests, persisting a local runtime-verification marker for staged
  versions, refusing to reuse a drifted local runtime directory, fencing
  `source-local` to the product repo only, and failing closed if a consumer
  launcher or repair path drifts outside `.odylith/runtime/versions/`.

- Verification: Source implementation is landed and focused install/runtime
  tests are passing locally. The bug remains open until the restarted hosted
  `v0.1.0` preview proves consumer rehearsal successfully.

- Prevention: Keep the public install contract on Odylith-managed runtime
  bundles, pin the upstream managed-Python archive digests, persist local
  runtime-verification markers, restrict active runtime pointers and launcher
  fallbacks to `.odylith/runtime/versions/`, scrub ambient Python/toolchain
  selector environment variables, and state supported platforms explicitly in
  README, install docs, and Release/Odylith component specs.

- Detected By: Hosted prelaunch consumer rehearsal against the abandoned
  `v0.1.0` drill assets.

- Failure Signature: Hosted `install.sh` selected `python3` on the consumer
  machine, created a venv with Python `3.11.2`, and then failed because the
  Odylith wheel requires `>=3.13`.

- Trigger Path: `make consumer-rehearsal VERSION=0.1.0` after cutting the
  abandoned prelaunch drill assets.

- Ownership: Release/install runtime bootstrap contract.

- Timeline: The abandoned `v0.1.0` prelaunch drill was cut successfully and
  the product repo returned to pinned dog-food posture, but the first hosted
  consumer rehearsal then failed immediately on the machine-Python bootstrap
  assumption.

- Blast Radius: Any first-time consumer install on a machine without an
  already-compatible Python `3.13+` interpreter.

- SLO/SLA Impact: Release credibility and onboarding UX are blocked for the
  restarted preview relaunch.

- Data Risk: None.

- Security/Compliance: The failure is operational, but the bootstrap contract is
  weaker than intended because runtime ownership still depends on consumer
  system state. The forward fix must preserve strict runtime isolation and
  fail closed if consumer repos drift toward host-Python execution.

- Invariant Violated: Odylith first install should not depend on consumer-owned
  Python state for supported platforms.

- Workaround: Install Python `3.13+` manually before running the abandoned
  hosted installer. This workaround is intentionally temporary and not the
  desired product posture.

- Rollback/Forward Fix: Forward fix only. The restarted preview release should
  replace the bootstrap dependency with Odylith-managed runtime bundles.

- Agent Guardrails: Do not reintroduce consumer-machine Python as the public
  first-install dependency for supported platforms. Do not let consumer repos
  activate `source-local` or silently fall back to host Python during repair.

- Preflight Checks: Inspect this bug, the active B-005 plan, and the Release
  component spec before touching the public installer or release runtime
  staging path.

- Regression Tests Added: `tests/unit/install/test_python_env.py`,
  `tests/unit/install/test_runtime.py`,
  `tests/unit/install/test_release_bootstrap.py`,
  `tests/unit/install/test_release_assets.py`,
  `tests/integration/install/test_manager.py`,
  `tests/integration/install/test_lifecycle_simulator.py`.

- Monitoring Updates: Consumer rehearsal remains the canonical live proof until
  the managed-runtime lane is stable.

- Related Incidents/Bugs: None in the repo before this prelaunch rehearsal.

- Version/Build: Abandoned prelaunch `v0.1.0` drill assets.

- Config/Flags: `make consumer-rehearsal VERSION=0.1.0`.

- Customer Comms: No canonical public release should repeat this defect. The
  restarted preview line must use Odylith-managed runtime bundles for the
  supported first-install contract and still requires one successful hosted
  consumer rehearsal before broader confidence.

- Code References: Hosted release installer asset-generation lane,
  `src/odylith/install/managed_runtime.py`,
  `src/odylith/install/python_env.py`, `src/odylith/install/runtime.py`,
  `src/odylith/install/release_assets.py`, `src/odylith/install/manager.py`,
  `bin/consumer-rehearsal`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
