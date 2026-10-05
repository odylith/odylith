- Bug ID: CB-357

## Selected authoring and root recovery verified (2026-10-04)

Both update and scaffold now forward validated diagram IDs to the existing
refresh owner. Independent final review passes 10 actual-chain controls, seven
direct/global/cache controls and the unchanged original scaffold reproduction,
with no actionable P0/P1/P2. Authored dates and every unrelated row/asset remain
unchanged; failures retain exact selected retry advice. Final review:
/private/tmp/odylith-atlas-update-scope-independent-rereview-20261004.md,
SHA-256 6a1f8379073950a3e8275ea30847dac6a8322f63349758348933e6cea693fc73.

Root retained the accidental catalog, verified its exact hash and original
HEAD, restored only its catalog edits and replayed D-025 through the corrected
CLI with an actual review date. Replay succeeds; D-025 is the sole changed
catalog entry and every unrelated object equals HEAD. MMD/SVG/PNG retain their
reviewed hashes. Receipt:
/private/tmp/odylith-atlas-update-scope-recovery-20261004/receipt.json.
Original failed review and red controls remain unchanged. Full frozen runtime,
installation and release proof remain open.

## Independent authoring coverage correction (2026-10-04)

The first selected-update fix passes 166 bounded checks, but independent
actual-chain review finds the second authoring caller, `atlas scaffold`, still
uses an unscoped refresh. A new selected diagram changes all three unrelated
fixture review dates and fingerprints, then advises a global retry. This P1
partial-adoption finding is retained before extending the same validated scope
to scaffold; selected-update and omitted-date controls otherwise pass.
Review: /private/tmp/odylith-atlas-update-scope-independent-review-20261004.md,
SHA-256 19e1d08172a57bc8b30490da4aa9e3e467e52771720f70ff2a2db0170289bdee.
Recovery and release status remain pending corrected independent verification.

- Status: FixedPendingRelease

- Created: 2026-10-04

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Canonical atlas update for D-025 changed review dates and watched-content fingerprints on 35 unrelated catalog rows. The update contract preserves omitted fields. Its owned Atlas refresh silently enables full atlas-sync, which issues auto-update --all-stale. Explicit full sync is intentional; a selected update does not authorize unrelated review acknowledgement.

- Impact: Unrelated Atlas diagrams appear freshly reviewed without selected review, corrupting historically useful freshness evidence.

- Components Affected: atlas

- Environment(s): Product repo detached source-local, existing v0.1.15 branch, catalog clean before root-owned D-025 update.

- Detected By: Maintainer catalog diff and independent bounded Atlas scope diagnosis

- Failure Signature: A D-025-only atlas update mutates 36 entries; 35 unrelated entries change only review markers.

- Trigger Path: atlas update -> owned_surface_refresh atlas_sync -> sync_workstream_artifacts --all-stale

- Ownership: Atlas explicit metadata writer and existing shared owned-surface refresh owners

- Timeline: Captured 2026-10-04 through `odylith bug capture`.

- Blast Radius: Installed consumer and maintainer selected Atlas updates; all unrelated review evidence.

- SLO/SLA Impact: Governance freshness correctness; no render latency breach demonstrated.

- Data Risk: Unrelated review-marker evidence is overwritten; original HEAD and exact pre-recovery catalog are retained.

- Security/Compliance: No security or compliance incident demonstrated.

- Invariant Violated: An explicit selected-diagram update must not acknowledge unrelated watched-content or review-age debt.

- Root Cause: Selected diagram IDs are lost at the shared refresh boundary, which defaults Atlas authoring to global stale acknowledgement.

- Solution: Forward validated exact diagram IDs through existing refresh, auto-update, freshness checks and cache identity; preserve explicit full-sync semantics.

- Verification: Retain /private/tmp/odylith-atlas-update-review-scope-diagnosis-20261004.md and exact /private/tmp/odylith-atlas-update-scope-recovery-20261004 catalog copies. Prove real selected/batch chain, invalid/no-write controls, explicit full-sync parity, honest unrelated stale debt and root corrected CLI replay.

- Prevention: Test actual authoring refresh chain rather than only mocked refresh; exact selection scope must survive cache and final freshness checks.

- Related Incidents/Bugs: CB-097/098 closed content/render truth; CB-112 owned refresh; B-133 H1 flow; B-142 shared non-regression

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/surfaces/update_mermaid_diagram.py
- src/odylith/runtime/governance/owned_surface_refresh.py
- src/odylith/runtime/governance/sync_workstream_artifacts.py
- src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py
- src/odylith/runtime/surfaces/scaffold_mermaid_diagram.py
