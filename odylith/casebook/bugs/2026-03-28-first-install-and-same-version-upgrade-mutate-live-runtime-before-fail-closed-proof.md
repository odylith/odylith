- Bug ID: CB-003

- Status: Open

- Created: 2026-03-28

- Severity: P1

- Reproducibility: Intermittent

- Type: Product

- Description: Fresh consumer install promoted the managed runtime live before
  the full-stack context-engine pack and activation smoke had completed, and a
  same-version `odylith upgrade` could restage the live runtime path in place
  instead of treating that case as a no-op or repair flow.

- Impact: A first install could leave a partially prepared live runtime if the
  post-activation smoke failed after the base runtime had already been made
  current, and a same-version upgrade could weaken rollback and pack-reuse
  safety by touching the active runtime when no real version transition was
  happening.

- Components Affected: `src/odylith/install/manager.py`,
  `src/odylith/install/runtime.py`, fresh consumer install lifecycle,
  same-version upgrade contract, install smoke coverage.

- Environment(s): Consumer first install, pinned upgrade retry, and any
  request that resolves to the already active verified version.

- Root Cause: Install promoted the base managed runtime before the full stack
  was proven live, while upgrade assumed every requested release should be
  restaged even when the target version already matched the active runtime.

- Solution: Keep fresh consumer install staged until the managed context-engine
  pack is applied and the activation smoke passes, clear the live pointer and
  launcher on first-install smoke failure, and make same-version upgrade a
  no-op for healthy verified full-stack runtimes while directing drifted cases
  to `odylith doctor --repo-root . --repair`.

- Verification: Added regression coverage for install smoke with scrubbed
  environment, first-install failure cleanup, same-version upgrade no-op
  behavior, same-version fail-closed repair guidance when the full-stack pack
  is missing, and rejection of untrusted previous-pack paths during reuse.

- Prevention: Do not mutate the live runtime when there is no real version
  transition. First install and repair should fail closed until the full-stack
  runtime passes activation smoke.

- Detected By: Final relaunch hardening pass on
  `2026/freedom/release-reset-runtime-footprint`.

- Failure Signature: First install could leave `.odylith/runtime/current`
  pointing at a base-only runtime after smoke failure, and a same-version
  upgrade could restage `.odylith/runtime/versions/<active>` even though the
  operator had not asked for a version change.

- Trigger Path: `odylith install`, `odylith upgrade`, and context-engine-pack
  reuse during an upgrade that targets the already active version.

- Ownership: Install/runtime lifecycle contract.

- Timeline: The relaunch slice already split runtime transport and added
  release proof; this follow-on hardening pass closed the remaining live-path
  activation gap.

- Blast Radius: Consumer first install, no-op upgrade retries, and repair-like
  operator behavior during release transitions.

- SLO/SLA Impact: Reliability and rollback posture degrade if the live runtime
  can be touched before the full stack is proven healthy.

- Data Risk: Low but real. Live runtime selection and launcher state could
  briefly point at a runtime that had not yet completed full-stack activation.

- Security/Compliance: Failing closed before live activation reduces ambiguity
  around what runtime and feature-pack state the repo is actually executing.

- Invariant Violated: Odylith should not expose a live full-stack runtime until
  the full stack is staged and smoke-checked, and same-version upgrade should
  not restage the active runtime in place.

- Workaround: Use `odylith doctor --repo-root . --repair` to safely restage the
  pinned runtime when the active version already matches the target.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not reintroduce live same-version restaging or
  promote fresh installs live before the full-stack smoke passes.

- Preflight Checks: Inspect the Install and Upgrade runbook plus the Odylith
  and Release component specs before changing install or upgrade activation
  rules.

- Regression Tests Added: `tests/integration/install/test_manager.py`

- Monitoring Updates: None.

- Related Incidents/Bugs: `2026-03-28-release-download-cache-and-runtime-restage-lose-atomicity-on-failure.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: None.

- Customer Comms: None.

- Code References: `src/odylith/install/manager.py`,
  `src/odylith/install/runtime.py`,
  `src/odylith/install/state.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
