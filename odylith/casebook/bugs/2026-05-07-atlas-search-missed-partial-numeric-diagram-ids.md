- Bug ID: CB-179

- Status: FixedPendingRelease

- Created: 2026-05-07

- Severity: P2

- Reproducibility: High

- Type: UX

- Description: Atlas search missed partial numeric diagram ids

- Impact: Operators searching Atlas by the numeric part of a diagram id, such as 003 for D-003, could fail to land on the intended diagram even though the id was visible in the catalog.

- Components Affected: atlas

- Environment(s): Odylith product repo v0.1.15 source-local maintainer posture; generated Atlas catalog UI.

- Detected By: Operator feedback on 2026-05-07 and browser search regression using query 003.

- Failure Signature: Atlas search indexed the displayed D-### id but did not carry compact and numeric diagram-id tokens into filtering and active-detail selection.

- Trigger Path: Open odylith/index.html?tab=atlas and search for 003.

- Ownership: Atlas catalog search indexing, active diagram selection, and browser search proof.

- Timeline: Captured 2026-05-07 through `odylith bug capture`.

- Blast Radius: Atlas diagram lookup, greenfield topology review, and support workflows that refer to diagrams by short numeric ids.

- SLO/SLA Impact: No outage; adds manual lookup time and makes diagram references feel unreliable.

- Data Risk: No application data risk; generated topology navigation can be incomplete.

- Security/Compliance: Accessibility and policy posture: the search control must resolve visible identifiers by their common shorthand for keyboard users and support operators; no credential, privacy, or safety exposure.

- Invariant Violated: Atlas search must match canonical diagram ids, compact ids, and numeric id fragments such as 003.

- Root Cause: Search text did not include canonical compact/numeric diagram tokens, and the active-detail selection did not prefer an exact diagram-id token hit when broader workstream text also matched.

- Solution: Index D-003, D003, 003, and 3 tokens for each diagram id and prefer an exact diagram-id token match as the active detail after filtering.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_mermaid_catalog.py::test_render_mermaid_catalog_indexes_diagram_ids_for_short_search_tokens tests/integration/runtime/test_atlas_sort_browser.py::test_atlas_search_matches_partial_diagram_number

- Prevention: Keep a browser test that searches 003 and requires D-003 to be visible and active.

- Regression Tests Added: tests/unit/runtime/test_render_mermaid_catalog.py and tests/integration/runtime/test_atlas_sort_browser.py.

- Code References: - src/odylith/runtime/surfaces/render_mermaid_catalog.py
- tests/unit/runtime/test_render_mermaid_catalog.py
- tests/integration/runtime/test_atlas_sort_browser.py
