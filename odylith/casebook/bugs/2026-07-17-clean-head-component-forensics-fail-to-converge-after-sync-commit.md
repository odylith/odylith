- Bug ID: CB-270

- Status: Open

- Created: 2026-07-17

- Severity: P1

- Reproducibility: Always

- Type: Tooling

- Description: A pinned release runtime can author component forensics for an unreleased product-repo source tree; the next source-local release preflight then detects the resulting stale domain-intelligence FORENSICS.v1.json.

- Impact: Release assembly is blocked before fresh installed-runtime proof can begin.

- Components Affected: registry

- Environment(s): Odylith product-repo maintainer branch 2026/freedom/v0.1.15, with the repo-local launcher in pinned_release posture while the checked-out source has diverged from the pin.

- Detected By: Disposable local-release-assets preflight.

- Failure Signature: sync component spec requirements FAILED: stale specs: odylith/registry/source/components/domain-intelligence/FORENSICS.v1.json

- Trigger Path: Change product source; use the pinned repo-local launcher to run governance sync-component-spec-requirements; commit its output; then run source-local local-release-assets from the clean head.

- Ownership: Registry forensics projection and release preflight boundary.

- Timeline: Captured 2026-07-17 after ce3b91a46 passed the pinned-runtime check before commit and failed source-local local-release-assets after commit. Source-local sync then converged without another generated change.

- Blast Radius: Any release that changes a component contract or mapped source path.

- SLO/SLA Impact: Blocks release assembly and delays installed consumer acceptance proof.

- Data Risk: No user data loss observed; release reliability risk only.

- Security/Compliance: No credential or compliance exposure observed.

- Invariant Violated: A clean committed component-forensics projection must converge under check-only release preflight.

- Workaround: Regenerate governed source from the explicit source-local maintainer posture, then verify source-local check-only convergence before package assembly.

- Root Cause: The pinned release runtime and the unreleased source-local synchronizer produced different forensics. The pinned runtime preserved a workspace_activity event that the source-local synchronizer correctly excludes from committed sidecars.

- Solution: Keep pinned runtime for shipped-package proof only. Use explicit source-local authoring and source-local check-only convergence whenever governed artifacts must reflect unreleased product source.

- Rollback/Forward Fix: No product-code rollback. Resume fresh distribution proof only after source-local regeneration and a clean-head source-local check-only pass.

- Verification: Confirm pinned-runtime and source-local posture with odylith version; run source-local synchronization and source-local check-only from the exact clean head; then pass local-release-assets and the installed matrix.

- Prevention: Release preflight must require clean-head source-local component-forensics convergence before asset assembly.

- Agent Guardrails: Do not use pinned runtime to author governed artifacts for unreleased product source, and do not bypass a source-local release gate with repeated sync-and-commit cycles.

- Preflight Checks: Run PYTHONPATH=src .venv/bin/python -m odylith.cli governance sync-component-spec-requirements --repo-root . --check-only from the exact clean commit to be packaged.

- Monitoring Updates: Release proof records the maintainer runtime posture and the clean-head source-local convergence result.

- Version/Build: 0.1.15 commit ce3b91a46.

- Config/Flags: Default local-release-assets path.

- Customer Comms: None; caught before release.

- Related Incidents/Bugs: CB-232

- Code References: - src/odylith/runtime/governance/sync_component_spec_requirements.py
- bin/_odylith.sh
