- Bug ID: CB-009

- Status: Open

- Created: 2026-03-28

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: Building the managed context-engine feature pack for supported
  Linux targets failed because the release asset publisher required a
  `watchdog` wheel that does not exist for that target platform.

- Impact: The canonical release asset lane could not complete across all
  supported platforms, which blocked the relaunch proof even though Odylith's
  runtime watcher ladder already supports `git-fsmonitor` and polling when
  `watchdog` is unavailable.

- Components Affected: `src/odylith/install/managed_runtime.py`, release asset
  publisher, release asset build lane, context-engine watcher acceleration
  contract.

- Environment(s): maintainer release asset build for `linux-arm64` and
  `linux-x86_64`.

- Root Cause: The context-engine feature pack treated `watchdog` as a universal
  wheel dependency instead of a platform-specific watcher accelerator.

- Solution: Keep the full context-engine pack as the default install outcome,
  but make its dependency set platform-aware: omit `watchdog` from Linux pack
  assembly and rely on the existing watcher fallback order (`watchman ->
  watchdog -> git-fsmonitor -> poll`) there.

- Verification: Source fix landed with a unit test proving the pack excludes
  `watchdog` on supported Linux platforms. The bug remains open until local
  hosted-asset proof completes successfully across the generated release asset
  set.

- Prevention: Treat watcher accelerators as optional per-platform inputs unless
  wheel availability is proven for every supported runtime target.

- Detected By: Manual local hosted-asset proof while publishing relaunch
  assets.

- Failure Signature: `pip download --platform manylinux_2_17_aarch64 ...`
  failed with `No matching distribution found for watchdog<7.0,>=6.0`.

- Trigger Path: release asset publish while building the Linux
  `odylith-context-engine-memory-*.tar.gz` bundles.

- Ownership: Managed runtime feature-pack packaging and release asset build
  contract.

- Timeline: The full-stack pack split landed first, then the first local
  hosted-asset proof exposed that `watchdog` was not actually available on one
  supported Linux target.

- Blast Radius: Any release cut that includes supported Linux platforms.

- SLO/SLA Impact: Release availability and platform support reliability are
  blocked.

- Data Risk: None.

- Security/Compliance: The forward fix preserves signed asset verification and
  does not weaken runtime isolation.

- Invariant Violated: Supported-platform release asset generation should not
  fail on an optional watcher accelerator wheel.

- Workaround: Remove `watchdog` manually from the Linux target pack
  requirements. The forward fix encodes that behavior in source.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not drop `linux-arm64` support or weaken signed release
  proof to dodge this platform gap.

- Preflight Checks: Inspect this bug, the odylith-context-engine spec, and the
  release component spec before changing watcher-packaging rules again.

- Regression Tests Added: `tests/unit/install/test_release_bootstrap.py`

- Monitoring Updates: `odylith doctor` and `odylith version` should continue
  to report context-engine mode and watcher readiness independently of
  `watchdog` presence.

- Related Incidents/Bugs: `2026-03-28-release-preflight-fails-when-dist-contains-stale-wheel.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: none.

- Customer Comms: Odylith still installs the full context-engine stack by
  default. On Linux, watcher acceleration may skip `watchdog` and rely on the
  next supported watcher backend automatically.

- Code References: `src/odylith/install/managed_runtime.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine.py`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
