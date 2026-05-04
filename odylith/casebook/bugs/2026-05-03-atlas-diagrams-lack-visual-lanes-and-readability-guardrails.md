- Bug ID: CB-162

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-03

- Severity: P2

- Reproducibility: Always

- Type: UX

- Description: Atlas diagrams could be architecturally useful but visually bland: generated flowcharts lacked diagram-internal lane grouping where useful, semantic color grouping, and a clear readability contract for long labels. The viewer also needed explicit padded-fit proof while keeping its canvas plain white.

- Impact: Operators reviewing Atlas topology get less value from otherwise useful diagrams because component placement, semantic grouping, and visual hierarchy are harder to scan; long labels are at higher risk of clipping or becoming unreadable.

- Components Affected: atlas

- Environment(s): Odylith v0.1.14 maintainer branch, Atlas generated flowcharts, greenfield proposal Atlas drafts, and the Atlas browser viewer.

- Detected By: Operator feedback on 2026-05-03 that Atlas diagrams are great but bland and should use lanes, subtle colors, better placement, typography, and safeguards against hidden or overwritten text.

- Failure Signature: Starter and host-authored flowcharts can render as same-plane boxes with no useful grouping or semantic color classes; Atlas viewer did not prove diagram images fit inside the stage with readable padding.

- Trigger Path: Create or apply Atlas flowchart diagrams through odylith atlas scaffold or greenfield apply, then open odylith/index.html?tab=atlas and inspect the diagram viewer.

- Ownership: Atlas Mermaid scaffold, greenfield proposal validation, and Atlas browser viewer rendering.

- Timeline: Captured 2026-05-03 during v0.1.14 Atlas UX hardening after greenfield and Casebook visual feedback.

- Blast Radius: All new consumer Atlas flowchart diagrams and greenfield Atlas drafts, plus operators reviewing diagrams in the generated Atlas surface.

- SLO/SLA Impact: No service outage; material architecture-readability and onboarding-quality degradation.

- Data Risk: None for application data; low governance-quality risk because topology can be technically linked but visually weak.

- Security/Compliance: No direct security impact.

- Invariant Violated: Atlas topology should communicate placement and semantic grouping clearly, and the viewer must not clip or hide diagram text on first paint.

- Root Cause: Atlas scaffold generated a generic node fan-out without a visual grammar, greenfield proposal validation accepted unstyled flowcharts, Mermaid rendering used raw default theme posture, and viewer fit tests covered header fact cards but not diagram image clipping. The first color pass also overreached by manipulating the viewer background instead of limiting polish to diagram-internal containers and nodes.

- Solution: Add a scaffold template with diagram-internal lanes where useful, subtle classDef/style colors, and wrapped labels; require greenfield flowchart Mermaid to include subtle diagram-internal colors and wrapped long labels; add a shared Mermaid render theme for polished diagram-internal typography/colors/edges; keep the Atlas viewer canvas plain white while adding padded fit math plus browser proof. The final v0.1.14 palette is deterministic: authored Mermaid remains topology truth, Atlas owns rendered fill/stroke/text color so old and new diagrams share one darker managed scheme, container colors only communicate grouping, inner node colors communicate broad semantic role, the decision/gate bucket uses soft peach/coral instead of amber, and neutral fallback remains available when labels do not match a role.

- Rollback/Forward Fix: Forward fix in Atlas scaffold, greenfield validation, renderer CSS/fit logic, and browser tests for v0.1.14.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_owned_surface_refresh_authoring.py tests/unit/runtime/test_greenfield_proposals.py tests/unit/install/test_atlas_surface_migration.py tests/integration/install/test_lifecycle_simulator.py (`56 passed`); PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_diagram_freshness.py tests/unit/runtime/test_surface_shell_contracts.py tests/integration/runtime/test_surface_browser_layout_audit.py::test_atlas_viewer_uses_plain_white_stage_and_fits_diagram_without_clipping tests/integration/runtime/test_atlas_sort_browser.py (`85 passed`); PYTHONPATH=src python -m pytest -q tests/unit/install/test_migration_runtime.py tests/unit/runtime/test_component_registry_intelligence.py tests/unit/runtime/test_workstream_inference.py (`75 passed`); peach/coral replacement proof passed `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_greenfield_proposals.py tests/unit/install/test_atlas_surface_migration.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_diagram_freshness.py` (`67 passed`) and Atlas browser proof (`4 passed`); `odylith atlas auto-update --repo-root . --all-stale --runtime-mode standalone` rendered 43 diagrams fresh; `odylith atlas render --repo-root . --fail-on-stale --runtime-mode standalone` reported 43 fresh and 0 stale; `git diff --check` passed.

- Prevention: Keep flowchart visual-contract validation, render-style fingerprints, Atlas migration proof, and browser image-fit proof so future Atlas diagrams cannot regress to unstyled single-plane boxes, viewer-background decoration, stale generated SVG/PNG assets, or clipped first-paint SVGs.

- Regression Tests Added: tests/unit/runtime/test_owned_surface_refresh_authoring.py::test_atlas_scaffold_allows_atlas_first_draft_without_governance_links; tests/unit/runtime/test_greenfield_proposals.py flowchart visual contract tests; tests/unit/runtime/test_render_mermaid_catalog.py::test_render_mermaid_catalog_keeps_viewer_stage_plain_white; tests/integration/runtime/test_surface_browser_layout_audit.py::test_atlas_viewer_uses_plain_white_stage_and_fits_diagram_without_clipping

- Monitoring Updates: Watch consumer greenfield Atlas screenshots for lane grouping, semantic color classes, and readable first-paint diagram fit.

- Related Incidents/Bugs: CB-159, CB-160

- Fixed In: 0.1.14

- Code References: - src/odylith/runtime/surfaces/scaffold_mermaid_diagram.py
- src/odylith/runtime/domain_intelligence/proposal_validation.py
- src/odylith/runtime/surfaces/render_mermaid_catalog.py
- src/odylith/runtime/surfaces/assets/mermaid_render_config.json
- src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs
- src/odylith/install/atlas_surface_migration.py
- tests/integration/runtime/test_surface_browser_layout_audit.py
