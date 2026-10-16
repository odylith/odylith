- Bug ID: CB-267

- Status: Open

- Created: 2026-07-17

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: Normalized setup action can become the canonical greenfield title

- Impact: A confirmed consumer intent can compile to a project title that describes setup work instead of the product, degrading every pre-confirm review surface.

- Components Affected: domain-intelligence

- Environment(s): Maintainer source-local runtime suite on branch 2026/freedom/v0.1.15

- Detected By: Full runtime suite replay

- Failure Signature: test_confirmed_json_intent_repairs_prompt_shaped_title returned Choose Approved Public Data Watchlist instead of Tracked Person Profile Watchlist

- Trigger Path: normalize_confirmed_intent -> normalize_first_path -> complete_confirmed_intent -> derived_title

- Ownership: Domain Intelligence confirmed-title completion

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: Any confirmation whose normalized first path starts with a base-form setup action and whose durable state provides the stronger product identity.

- SLO/SLA Impact: Pre-confirm review remains deterministic but presents an inaccurate package identity, increasing operator correction cost and confirmation risk.

- Data Risk: No governed write occurred; the defect was detected during pre-confirm compilation.

- Security/Compliance: No security or compliance impact.

- Invariant Violated: Canonical project titles must represent durable product state or capability, never an intermediate setup action.
