- Bug ID: CB-232

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-07-10

- Severity: P1

- Reproducibility: Always

- Type: Tooling

- Description: The component-forensics synchronizer persists synthetic workspace activity generated from dirty working-tree paths. After those paths are committed, a clean release build recomputes different forensic bytes and rejects a valid release.

- Impact: Maintainers can be blocked from building a fresh release after a normal governance sync and commit cycle.

- Components Affected: registry

- Environment(s): Odylith product-repo maintainer branch 2026/freedom/v0.1.15 during local-release-assets preflight.

- Detected By: Adversarial installed-package custody audit and local release build preflight.

- Failure Signature: local-release-assets reports Registry component forensics are stale immediately after the prior sync output was committed.

- Trigger Path: Run governance sync-component-spec-requirements while source changes are dirty, commit the generated output, then run make local-release-assets from the clean commit.

- Ownership: Registry forensics projection and release preflight boundary.

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: Any product-repo release whose component specs or mapped source paths change before component-forensics synchronization.

- SLO/SLA Impact: Release assembly fails before package creation and delays installed consumer proof.

- Data Risk: No user data loss. The failure is release-gate churn.

- Security/Compliance: No credential or regulated-data exposure observed.

- Invariant Violated: Committed component-forensics bytes must be deterministic for the same clean source tree.

- Workaround: Commit source/spec changes, resynchronize from the clean commit, and commit the settled sidecar before rebuilding.

- Root Cause: Workspace activity is derived from git status and persisted into FORENSICS.v1.json even though it changes when the synchronized files are committed.

- Solution: Keep volatile workspace activity out of committed forensic sidecars and compute it only for live Registry visibility.

- Rollback/Forward Fix: Forward fix landed in the Registry forensics projection. The two-pass workaround is no longer required for clean-head release preflight.

- Verification: Focused synchronization and Registry intelligence coverage passed 15 tests. A clean-head check-only run after commit 9606871db passed with zero stale paths. Fresh local-release assets then assembled successfully and the installed 14-case release matrix passed with browser, leakage, cleanup, and rescue proof.

- Prevention: Release preflight must test sync, commit-equivalent clean state, and check-only convergence.

- Agent Guardrails: Do not persist git-status observations in source-controlled forensic records.

- Preflight Checks: Run component-forensics check-only after a clean commit before package assembly.

- Monitoring Updates: Release proof records whether component-forensics check-only passed from a clean worktree.

- Version/Build: 0.1.15 fresh installed dist 9606871db

- Config/Flags: Default local release assets path.

- Customer Comms: None; caught before release.

- Related Incidents/Bugs: CB-229, CB-231

- Fixed In: 0.1.15 release proof verified; shipment pending

- Code References: - bin/_odylith.sh
- src/odylith/runtime/governance/sync_component_spec_requirements.py
- tests/unit/runtime/test_sync_component_spec_requirements.py
