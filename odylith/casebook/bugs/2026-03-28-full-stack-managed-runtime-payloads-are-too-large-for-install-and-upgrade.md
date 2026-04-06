- Bug ID: CB-005

- Status: Open

- Created: 2026-03-28

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: Odylith's managed runtime payloads grew large enough that first
  install, release upload, and incremental upgrade all moved one monolithic
  full-stack archive and retained multiple old copies on disk. The result was
  stalled transport and unnecessary repeated download churn.

- Impact: Full-stack Odylith remained the right default product posture, but
  the transport shape was too heavy for a smooth preview relaunch. Install and
  upgrade felt larger and slower than they needed to be, and release upload
  time grew with every repeated full-stack bundle.

- Components Affected: release asset build lane,
  `src/odylith/install/release_assets.py`, `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, release asset contract, runtime retention
  contract.

- Environment(s): local maintainer builds, local consumer install rehearsal,
  incremental upgrade between managed-runtime preview builds.

- Root Cause: Odylith packaged the full runtime stack as one large managed
  runtime bundle, then retained multiple staged versions and cached release
  copies even when only one active version plus one rollback target were
  operationally necessary.

- Solution: Keep full-stack install by default, but split release transport
  into a smaller base managed runtime plus a separately versioned managed
  context-engine pack, reuse an unchanged pack across upgrades when its asset
  digest matches, and prune staged runtimes plus release caches down to the
  active version and one rollback target.

- Verification: Source implementation is landed with focused release-asset,
  runtime, manager, and CLI tests passing locally. The bug remains open until
  maintainer preflight and hosted consumer rehearsal prove the lighter
  full-stack contract end to end.

- Prevention: Keep the user-facing contract full-stack, but do not let release
  transport collapse back into one oversized archive. Track pack digest/file
  metadata, prune retained versions automatically, and keep a blocking local
  hosted-asset smoke in `make release-preflight`.

- Detected By: Maintainer install/update size review during the preview-line
  relaunch reset.

- Failure Signature: Large runtime archives, repeated staged-version growth
  under `.odylith/runtime/versions/`, repeated cached release copies under
  `.odylith/cache/releases/`, and upgrade/download steps that felt stalled
  because the heavy context-engine payload moved every time.

- Trigger Path: Full-stack local install, local upgrade, and release-asset
  generation for the relaunch line.

- Ownership: Managed runtime packaging, retention, and release asset contract.

- Timeline: The managed-runtime lane solved the machine-Python bootstrap gap,
  but the resulting full-stack runtime payloads were still too heavy. The
  relaunch reset captured the transport/retention issue as a separate product
  bug and implemented the split-asset fix before the restarted `v0.1.0`
  preview.

- Blast Radius: Any downstream first install or upgrade on supported platforms,
  plus the maintainer release lane itself.

- SLO/SLA Impact: Preview release credibility and operator patience degrade
  when install/update transport stalls on avoidable payload size.

- Data Risk: None.

- Security/Compliance: The fix must preserve signed manifest/provenance/SBOM
  validation and runtime isolation while changing the packaging shape.

- Invariant Violated: Full-stack Odylith should not require oversized,
  repeatedly retained monolithic payloads when smaller managed assets can
  preserve the same runtime outcome.

- Workaround: None that preserves the intended full-stack product posture.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not "solve" this by downgrading the default install to a
  weaker product. Keep full-stack install as the default and optimize the asset
  transport and retention model instead.

- Preflight Checks: Inspect this bug, the active B-005 plan, and the Release /
  Odylith component specs before changing runtime packaging or retention again.

- Regression Tests Added: `tests/unit/install/test_release_assets.py`,
  `tests/unit/install/test_runtime.py`, `tests/unit/test_cli.py`,
  `tests/integration/install/test_manager.py`.

- Monitoring Updates: `odylith version` and `odylith doctor` now surface the
  context-engine pack state so maintainers can see whether the full-stack
  runtime outcome is intact.

- Related Incidents/Bugs: Prelaunch `0.1.x` rehearsal findings on machine
  Python bootstrap, rollback trust, and starter-tree seeding.

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: none.

- Customer Comms: Odylith keeps full-stack install by default. The relaunch
  changes the internal packaging shape so installs and upgrades move smaller,
  reusable assets underneath that default experience.

- Code References: `bin/release-preflight`,
  `src/odylith/install/managed_runtime.py`,
  `src/odylith/install/release_assets.py`,
  `src/odylith/install/runtime.py`, `src/odylith/install/manager.py`,
  `src/odylith/cli.py`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
