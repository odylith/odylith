- Bug ID: CB-338

- Status: Open

- Created: 2026-08-18

- Severity: P2

- Reproducibility: Always

- Type: Test

- Description: The canonical browser shard requires D-004 to be Fresh. Working-tree auto-update correctly refreshed seven changed-path diagrams but omitted D-004 because its stale reason comes from an already-committed Odylith component-spec change. The subsequent fail-on-stale render exposed 19 globally stale diagrams and exited after writing the seven bounded review updates.

- Impact: Operational release risk: the browser matrix fails and bounded changed-path refresh cannot by itself settle pre-existing committed watch drift.

- Components Affected: atlas

- Environment(s): Odylith product-repo detached source-local make dev-validate and Atlas auto-update

- Detected By: make dev-validate shard 2 browser matrix followed by atlas auto-update --from-git-working-tree --fail-on-stale

- Failure Signature: D-004 diagramFreshness never becomes Fresh; payload reports Linked implementation changed after diagram source update for odylith/registry/source/components/odylith/CURRENT_SPEC.md; catalog render reports 19 stale diagrams.

- Trigger Path: make dev-validate -> context_execution_alignment_browser D-004 -> atlas auto-update working-tree selection -> global freshness gate

- Ownership: Atlas change-watch freshness and release governance settlement

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: All Atlas browser tests and release gates that require globally fresh catalog truth.

- SLO/SLA Impact: Release validation SLO is blocked until the stale catalog review fingerprints are settled.

- Data Risk: No application data loss; governance architecture views can misrepresent review freshness.

- Security/Compliance: Security and compliance posture remain fail-closed; stale architecture review evidence cannot be promoted as current.

- Invariant Violated: A release candidate must have fresh Atlas source truth and rendered catalog state for every active diagram exercised by the browser matrix.

- Root Cause: Changed-path auto-update selects only current worktree impacts, while D-004 and other diagrams retained stale fingerprints from prior committed watch-path changes.

- Solution: Run the explicit all-stale Atlas review flow, rerender the catalog, and verify D-004 plus the full active catalog are Fresh; do not manually flip freshness metadata.

- Rollback/Forward Fix: Forward-fix governed Atlas review fingerprints and generated surfaces.

- Verification: atlas auto-update --all-stale --fail-on-stale; exact D-004 browser node; Atlas render tests; restart canonical validation.

- Prevention: Require global Atlas freshness settlement before full browser validation and release promotion, in addition to changed-path auto-update.

- Agent Guardrails: Never hand-edit freshness flags or suppress the browser assertion; use watched-path fingerprints and governed render commands.

- Preflight Checks: Inspect D-004 stale_reasons and confirm source diagram content remains valid before review-only refresh.

- Regression Tests Added: Existing browser freshness and Atlas render gates provide regression proof.

- Related Incidents/Bugs: CB-337

- Code References: - odylith/atlas/source/catalog/diagrams.v1.json
- src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py
- tests/integration/runtime/test_context_execution_alignment_browser.py
