- Bug ID: CB-195

- Status: FixedPendingRelease

- Created: 2026-05-09

- Severity: P1

- Reproducibility: Always

- Type: OperatorUX

- Description: Greenfield diagrams repeated full project prompt in view titles

- Impact: Greenfield architecture review became noisy and unscannable because every diagram title repeated the full project prompt before the actual view name.

- Components Affected: domain-intelligence

- Environment(s): Odylith v0.1.15 consumer greenfield propose/create flow for empty or docs-only repos.

- Detected By: Maintainer transcript review of a merchant-lending greenfield proposal preview.

- Failure Signature: Architecture review views rendered titles such as '<full project title> System Overview' and '<full project title> First Slice Flow' instead of concise view names.

- Trigger Path: odylith greenfield propose --repo-root . --prompt '<greenfield project intent>'

- Ownership: domain-intelligence proposal scaffold, robot-swarm profile, proposal Tribunal, and greenfield preview rendering

- Timeline: Captured 2026-05-09 through `odylith bug capture`.

- Blast Radius: All deterministic greenfield profiles that reused the project title in diagram title fields; preview text, Atlas catalog rows, and rendered governance views inherited the noise.

- SLO/SLA Impact: Review-latency risk increased because operators had to parse prompt-length prefixes before finding the architecture view purpose.

- Data Risk: No production data mutation; governance-review risk is that consumer source truth becomes harder to inspect and more likely to be accepted without meaningful diagram review.

- Security/Compliance: Regulated-prompt risk: compliance, safety, and approval review can be buried under repeated project-title noise, so architecture view titles must stay concise and decision-focused.

- Invariant Violated: Diagram titles must name the architecture view purpose; project identity belongs in the proposal intent, slug, summary, and surrounding context, not as a repeated title prefix.

- Root Cause: The generic, merchant-lending, and robot-swarm diagram builders all used f'{title} <view name>' for every diagram title.

- Solution: Use concise view titles across deterministic greenfield diagram builders and add a Tribunal guard that rejects confirmed proposals whose diagram titles repeat the project title prefix.

- Rollback/Forward Fix: Forward fix only; slugs and summaries retain project context while titles become concise view names.

- Verification: Exact merchant-lending preview now renders Architecture review views as System Overview, First Slice Flow, Component Ownership Map, Domain State Model, and Validation And Release Topology without the prompt prefix. Focused generic, merchant-lending, robot-swarm, and compact-preview regression tests pass in source-local mode.

- Prevention: Regression tests assert concise diagram titles for generic, merchant-lending, and robot-swarm proposals, plus a Tribunal rejection for project-title-prefixed diagram titles.

- Agent Guardrails: When reviewing greenfield output, inspect generated view titles separately from slugs and summaries; slugs may encode project identity, titles should stay short and scannable.

- Preflight Checks: Run focused greenfield Atlas/profile tests and an exact CLI preview repro before release.

- Regression Tests Added: tests/unit/runtime/test_greenfield_atlas_contract.py::test_greenfield_apply_ready_scaffold_has_multi_view_architecture_suite; tests/unit/runtime/test_greenfield_atlas_contract.py::test_robot_swarm_greenfield_scaffold_expands_domain_specific_atlas_suite; tests/unit/runtime/test_greenfield_atlas_contract.py::test_greenfield_tribunal_rejects_project_title_prefixed_diagram_titles; tests/unit/runtime/test_greenfield_merchant_lending_profile.py::test_shopify_stablecoin_merchant_lending_avoids_checkout_profile; tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_text_is_compact_product_preview_before_confirmed_write

- Version/Build: v0.1.15 maintainer source-local

- Related Incidents/Bugs: CB-182, CB-190, CB-191, CB-192, CB-194

- Code References: - src/odylith/runtime/domain_intelligence/proposal_scaffold.py
- src/odylith/runtime/domain_intelligence/robot_swarm_profile.py
- src/odylith/runtime/domain_intelligence/proposal_tribunal.py
