status: finished

idea_id: B-117

title: Discipline Surfaces And Release Proof

date: 2026-04-17

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: B-110 Odylith Discipline execution waves, Radar, technical plan, Registry, Atlas, Compass, benchmark proof, host guidance

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Queued through `odylith backlog create` from the current maintainer lane.

confidence: high

founder_override: yes

promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-17-adaptive-discipline-credit-safe-and-benchmark-proved.md

execution_model: standard

workstream_type: child

workstream_parent: B-110

workstream_children:

workstream_depends_on:

workstream_blocks:

related_diagram_ids: D-040, D-041

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
B-110 needs explicit child execution slices so Odylith Discipline can land through governed waves instead of collapsing governance, runtime, learning, host parity, benchmarks, and release proof into one unbounded record.

## Customer
Odylith maintainers and host-lane operators who need v0.1.11 Odylith Discipline work to stay decomposed, auditable, benchmark-proved, low-latency, and credit-safe across Codex, Claude, dogfood, and consumer lanes.

## Opportunity
Create bounded child workstreams under B-110 so each major platform slice has a clear owner, proof obligation, and wave gate while the umbrella retains the full Odylith Discipline loop.

## Proposed Solution
Keep the governed surfaces truthful while the runtime and host contracts move:
refresh Atlas, Compass, Radar, Registry, Casebook, and shell artifacts through
owned lanes, add the topology diagrams that explain the release-proof path, and
prove the rendered browser states before claiming the surface contract is clean.

## Scope
- Refresh the governed surfaces for Discipline and anti-slop hardening without
  widening into unrelated product work.
- Keep Atlas topology current for both release-proof DAGs and anti-slop
  cross-host parity.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
- B-110 execution waves are explicit and CLI-authorable\n- each child slice maps to one governance/runtime/proof concern\n- release targeting and wave status are visible in Radar and Compass\n- implementation can add focused tests without growing red-zone files

## Validation
- Completed with focused visible-intervention regression coverage, browser
  proof for rendered intervention surfaces, governed surface refresh proof, and
  prior full `make dev-validate` plus headless browser matrix proof.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Each child slice should strengthen the same Odylith Discipline platform: deterministic hard laws, adaptive stance, zero-credit hot paths, compact learning, subsystem integration, host parity, benchmark sovereignty, and public surface accountability.

## Impacted Components
- `odylith`

## Interface Changes
- Surface content, topology diagrams, and generated artifacts may change, but
  the public CLI and visible help/show behavior must remain stable.

## Migration/Compatibility
- No migration impact recorded yet.

## Test Strategy
- Add targeted regression coverage when implementation begins.

## Open Questions
- Which additional Atlas diagrams or surface proof lanes still need first-class
  governance after the current B-117 closeout?
