- Bug ID: CB-196

- Status: Open

- Created: 2026-05-11

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: Radar execution-wave summary wastes wide empty space

- Impact: Radar detail pages make execution-wave programs hard to scan because badges occupy a right-side strip while the summary leaves a large unused area inside the panel.

- Components Affected: radar

- Environment(s): Product repo dashboard, Radar workstream detail execution-wave section

- Detected By: User screenshot of Radar Execution Waves panel on 2026-05-10

- Failure Signature: Execution Waves summary shows a long program title and status badges at the top right, with large blank space under the badge column instead of a compact full-width summary.

- Trigger Path: Open Radar workstream detail for a greenfield umbrella workstream with execution waves, for example B-001 in the local mockrepo dashboard.

- Ownership: Shared execution-wave UI renderer for Radar and Compass surfaces

- Timeline: Captured 2026-05-11 through `odylith bug capture`.

- Blast Radius: Radar workstream detail pages that render umbrella-owned execution-wave programs; shared primitive must avoid regressing Compass.

- SLO/SLA Impact: Visual comprehension regression; no data loss, but slows review of wave status and first-build scope.

- Data Risk: None; presentation-only layout bug.

- Security/Compliance: None; no security or compliance data exposure.

- Invariant Violated: Execution-wave summaries must use the panel width efficiently and make program, status, and progress readable without dead layout space.
