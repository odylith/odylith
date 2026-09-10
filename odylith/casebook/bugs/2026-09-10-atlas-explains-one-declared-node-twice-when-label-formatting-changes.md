- Bug ID: CB-338

- Current Bounded Proof: The source correction retains case-sensitive IDs of explicitly emitted nodes and excludes those IDs from graph rediscovery. Four expanded counterexamples fail before the fix; ten identity controls and the full focused Atlas pack pass afterward (59 total). No regex, normalization helper or compatibility wrapper is added. D-042 has 17 source-authored explanations with exact visible-box coverage. Independent review runs the eleven new controls and finds no bounded P0/P1. Rendered and frozen broad proof below complete this bounded correction, not general Atlas parsing or Greenfield quality.

- Rendered Verification: The refreshed real shell passes ten desktop/mobile checks with exact D-042 label/description readback, no page or row overflow, and no browser errors. Root reviews all eighteen retained screenshots, including the complete D-042 explanation list. The shared identity correction removes 27 redundant explanation rows across 18 of 47 catalog diagrams; topology and diagram source are unchanged by that correction. Evidence: /private/tmp/odylith-migration-release-scope.nOTGQD/corrected-governance-readback.xml and corrected-*.png.

- Frozen Broad Validation: All 3,204 inputs match after every process completes: 5,058 runtime, 1,437 install, 180 CLI and 376 browser checks pass with zero failures or errors. One Radar browser check is skipped because its fixture lacks maintainer-only traceability diagnostics; it is not passing coverage. Evidence: /private/tmp/odylith-migration-release-scope.nOTGQD/atlas-*-full.xml and frozen-atlas-inputs.json. These are regression-suite durations, not consumer SLA measurements. Older clipped caption copy, generated-package quality, 60/90/120, installed release and automatic desktop chat-delivery proof remain open.

- Status: FixedPendingRelease

- Fixed In: 0.1.15

- Created: 2026-09-10

- Severity: P1

- Reproducibility: Always

- Type: UX

- Description: The Atlas detail inventory can explain one Mermaid node twice because explicit-label extraction and graph discovery key the same node by differently formatted display text. Current D-042 exposes this during actual desktop and mobile screenshot review.

- Impact: Readers see duplicate responsibilities and generic explanation copy that can misrepresent a governance or release boundary.

- Components Affected: atlas

- Environment(s): Detached source-local candidate based on 5fbc51b3, after unchanged-input runtime/install/CLI/browser qualification; D-042 real shell desktop and mobile.

- Detected By: Human screenshot review followed by three independent multiline-node counterexamples.

- Failure Signature: Two explicit nodes produce three explanation rows: Gateway RequestContract, Worker, and Gateway with a middle-dot RequestContract suffix.

- Trigger Path: Render a flowchart whose declared node has a multiline label with a contract subtitle, then inspect the Atlas diagram-box explanations.

- Ownership: Atlas box inventory joining explicit declarations to parsed graph nodes.

- Timeline: Captured 2026-09-10 through `odylith bug capture`.

- Blast Radius: Atlas flowcharts with label representations that differ between the two extraction passes; installed and staged views use this owner.

- SLO/SLA Impact: Violates clear differentiated diagram explanations; this is not a reason to relax Greenfield 60/90/120 limits.

- Data Risk: No consumer data writes were involved in the diagnostic; duplicate explanation can confuse ownership and proof interpretation.

- Security/Compliance: No exploit or authority bypass observed; do not mistake a misleading release explanation for transaction proof.

- Invariant Violated: One declared node has one identity regardless of display formatting; the explanation inventory must not create a second responsibility.

- Root Cause: Both extraction passes deduplicate by formatted label text rather than the existing case-sensitive Mermaid node ID.

- Solution: Preserve declared node identity across the two inventory passes, retain graph-only discovery, and supply reviewed source-owned D-042 descriptions for its actual labels.

- Verification: Private atlas-identity-red.xml records three failures and one passing case-sensitive control; atlas-copy-red.xml records six missing authored explanations. Evidence root: /private/tmp/odylith-migration-release-scope.nOTGQD/.

- Prevention: Keep structural identity independent of human display text. Browser success and schema validity do not replace screenshot review or authored-coverage controls.

- Related Incidents/Bugs: B-142; CB-337. Related CB-202/CB-208 history covers older Mermaid counting and typed-source boundaries, not this explanation rediscovery defect.

- Code References: - src/odylith/runtime/surfaces/atlas_box_explanations.py
