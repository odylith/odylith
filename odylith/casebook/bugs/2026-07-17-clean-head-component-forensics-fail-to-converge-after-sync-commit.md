- Bug ID: CB-270

## Repeated omitted-owner refresh in hosted CI (2026-10-15)

Both hosted suites at `433f0e38a` pass 11,209 tests and fail the same two
checks. The Release dossier check finds stale `FORENSICS.v1.json`.
Deriving its expected payload from the committed inputs identifies exactly
five missing durable Compass events: indices 1640, 1643, 1644, 1646 and 1647.
The Release timeline should contain 941 events rather than 936. Fourteen
component sidecars have only timeline and coverage differences; all 213
selected source inputs match the committed revision.

The final successful selective sync rendered Registry without invoking the
component-forensics owner. This repeats the ordering error documented below;
it is not Git workspace drift or a reason to weaken the convergence test.
After all intended logging and authored changes finish, run the canonical
component-spec synchronizer, require all-component check-only convergence,
and verify it again after the successor commit. Include every emitted
sidecar in the reviewed checkpoint. A successful render alone is insufficient.

The separate Casebook artifact failure is tracked in CB-305. Preserve both
failed hosted logs and the live benchmark's exact revision. This diagnosis
does not qualify a successor revision or the release. Exact derivation and
owner evidence are retained in
`/Users/freedom/.codex/odylith-release-evidence/2026-10-14/v52/post-volume-recovery-20261015T0458Z/canonical-release-forensics-CI-diagnosis.md`.

## Current generated Release evidence staleness (2026-10-13)

Both hosted CI runs for `11783fa0a` fail the unchanged release-dossier
convergence test. Push CI reports one failure, 10,889 passes and ten skips.
The exact same test also fails on the clean frozen `51c6a379f` checkout:
`release/FORENSICS.v1.json` is stale. Root's live version check confirms
detached source-local/source-checkout posture, so this occurrence is not
the historical pinned-runtime authoring mismatch described below.

The final source and governance changes were not followed by canonical
component-forensics settlement. A selective Registry render is insufficient
for that obligation. Refresh the registered component evidence through
`odylith governance sync-component-spec-requirements` after all source,
authored-record, Compass and surface writers settle. Require unchanged
check-only convergence on the resulting exact clean committed tree before
another long proof or package assembly. Preserve the test and its gate.

Full attempt `f1e495226c4d1a18` was stopped at the known-red checkpoint,
not scored or regraded. SIGINT did not retire the parent; the verified owned
process group was then terminated, returning 143. Original progress, logs
and interruption receipts are retained. The source checkout stays clean.
The obsolete 51c hosted runs were cancelled pending the corrected source.
No model, score, corpus, floor, validator or budget change is warranted.


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

- Preflight Checks: Run odylith governance sync-component-spec-requirements --repo-root . --check-only from the exact clean commit to be packaged.

- Monitoring Updates: Release proof records the maintainer runtime posture and the clean-head source-local convergence result.

- Version/Build: 0.1.15 commit ce3b91a46.

- Config/Flags: Default local-release-assets path.

- Customer Comms: None; caught before release.

- Related Incidents/Bugs: CB-232

- Code References: - src/odylith/runtime/governance/sync_component_spec_requirements.py
- bin/_odylith.sh
