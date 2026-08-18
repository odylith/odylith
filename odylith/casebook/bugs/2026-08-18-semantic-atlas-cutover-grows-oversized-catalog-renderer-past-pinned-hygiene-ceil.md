- Bug ID: CB-342

- Status: Open

- Created: 2026-08-18

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The graph-authority cutover added typed semantic diagram-box and presentation branches directly to render_mermaid_catalog.py. The file reached 3,408 lines while the explicit hygiene ceiling remained 3,363, exposing another ownership branch inside an already oversized hot file.

- Impact: Canonical validation fails, and continued semantic-versus-legacy branching inside the renderer increases maintenance and regression risk on a central operator surface.

- Components Affected: atlas

- Environment(s): Detached source-local maintainer worktree on 2026-08-18 during canonical dev-validation shard 12.

- Detected By: test_runtime_hotfile_inventory_stays_explicit_and_non_expanding.

- Failure Signature: oversized runtime owner grew past pinned limit: src/odylith/runtime/surfaces/render_mermaid_catalog.py; observed 3408, limit 3363.

- Trigger Path: PYTHONPATH=src .venv/bin/python -m pytest -q -x tests/unit/runtime/test_hygiene.py::test_runtime_hotfile_inventory_stays_explicit_and_non_expanding

- Ownership: Atlas catalog entry presentation boundary and source-file decomposition discipline.

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: Atlas render validation, semantic graph catalog materialization, legacy diagram presentation, and release hygiene gates.

- SLO/SLA Impact: Blocks release convergence; no installed consumer outage.

- Data Risk: No governed source data loss observed; duplicated presentation ownership can drift semantic diagram descriptions across rendered surfaces.

- Security/Compliance: No direct security or privacy exposure observed. The policy and operational-safety risk is reduced reviewability of provenance-sensitive Atlas output in a file already above the repository hard-pressure threshold.

- Invariant Violated: Graph-native semantic presentation and legacy inferred presentation must have one explicit adapter boundary, and oversized owners must not grow past pinned limits.

- Root Cause: Commit 555f72917 embedded semantic catalog validation and presentation branches directly in the monolithic renderer without moving that ownership or updating the hotfile guard.

- Solution: Extract one typed catalog-entry presentation adapter that owns semantic box validation and semantic-versus-legacy presentation selection, preserve lazy legacy imports, and reduce the renderer below its existing ceiling.

- Rollback/Forward Fix: Forward refactor only; do not increase the pinned ceiling or add a second semantic parser.

- Verification: Run semantic and legacy Atlas catalog tests, the hotfile hygiene node, the full renderer test file, and canonical shard 12.

- Prevention: Any future Atlas projection mode must enter through the catalog presentation adapter rather than adding branches to render_mermaid_catalog.py.

- Agent Guardrails: Do not normalize the line ceiling upward and do not fake-extract wrappers; move the full decision boundary and delete the old branch.

- Preflight Checks: Characterize semantic typed boxes, legacy narrative enrichment, and cold-import behavior before editing.

- Regression Tests Added: tests/unit/runtime/test_render_mermaid_catalog.py and tests/unit/runtime/test_hygiene.py

- Version/Build: Greenfield semantic graph source-local release candidate based on bf982b0e.

- Related Incidents/Bugs: CB-338, CB-341

- Code References: - src/odylith/runtime/surfaces/render_mermaid_catalog.py
- tests/unit/runtime/test_hygiene.py
