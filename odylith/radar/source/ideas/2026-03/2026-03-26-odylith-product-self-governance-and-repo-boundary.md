status: finished

idea_id: B-001

title: Odylith Product Self-Governance and Repo Boundary

date: 2026-03-26

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_lanes: both

impacted_parts: Odylith public repo governance roots, component registry, product component specs, bundle docs, installed product docs, and downstream repo-boundary references

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Odylith cannot honestly claim to be a separate product until the public repo governs itself and no downstream repo serves as the authoritative home for Odylith product records.

confidence: high

founder_override: yes

promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-26-odylith-product-self-governance-and-repo-boundary.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on:

workstream_blocks:

related_diagram_ids: D-001,D-002,D-003,D-004,D-005,D-006,D-007,D-008,D-009,D-010,D-011,D-012,D-013,D-014,D-015,D-016,D-017,D-018,D-019,D-020

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Odylith's runtime code already lives in the public repo, but the public repo still does not own the product's component registry, product component specs, or local governance records. That leaves a downstream repo acting like the product system of record.

## Customer
- Primary: maintainers shipping Odylith as a real installable product.
- Secondary: host repos that should adopt Odylith without inheriting Odylith's internal product-governance authorship.

## Opportunity
By letting the public repo govern itself, Odylith can ship a cleaner product boundary, cleaner public docs, and a clearer repo-integration contract.

## Proposed Solution
- add Odylith-owned product governance truth to the public repo;
- publish Odylith-owned component specs and registry data from the public repo;
- keep host-repo truth local to each repo;
- repoint downstream repos to installed Odylith docs and CLI surfaces instead of repo-local product records.

## Scope
- public Odylith component registry and component specs
- public Odylith Radar, Atlas, Casebook, Compass, and technical-plan roots
- installed-product doc materialization for component specs
- downstream repo reference cutover to installed Odylith product docs

## Non-Goals
- copying host-repo backlog, plan, bug, or diagram content into Odylith
- moving downstream repo runtime or domain code into Odylith
- introducing compatibility symlinks or host-specific public branding

## Risks
- public governance files can drift from product code if they are created but not used
- downstream repos can keep referencing stale local product docs if the cutover is incomplete
- bundle docs can diverge from public repo docs if the product-doc copy path is not maintained

## Dependencies
- none

## Success Metrics
- Odylith public repo has its own component registry and product component specs
- Odylith public repo has its own local Radar, Casebook, Atlas, Compass, and technical-plan roots
- host-repo product-component references resolve to installed `odylith/...` surface and runtime paths instead of repo-local product docs
- no host-repo-branded product truth is needed for Odylith product docs or registry entries

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit tests/integration`
- `PYTHONPATH=src python -m odylith.runtime.governance.validate_component_registry_contract --repo-root . --policy-mode advisory`

## Rollout
Land public Odylith self-governance first, then repoint downstream repo product references to the installed Odylith docs and command surface.

## Why Now
The runtime extraction is already far enough along that the missing piece is authority, not scaffolding. This is the point where Odylith becomes the source for itself.

## Product View
Odylith should not depend on another repo to explain what Odylith is. The product needs to own its own vocabulary, specs, surfaces, and evidence if it is going to be credible as a standalone system.

## Impacted Components
- `odylith`
- `dashboard`
- `radar`
- `atlas`
- `compass`
- `registry`
- `casebook`
- `odylith-context-engine`
- `subagent-router`
- `subagent-orchestrator`
- `tribunal`
- `remediator`

## Interface Changes
- public Odylith now carries product-owned component specs and component registry truth
- public Odylith now keeps canonical current specs under `odylith/registry/source/components/<component-id>/CURRENT_SPEC.md`
- public Odylith now carries repo-local governance roots for its own product work
- host repos should reference installed `odylith/...` surface and runtime paths for Odylith product component docs

## Migration/Compatibility
- this does not copy host-repo truth into Odylith
- host repos keep their own local Radar, Casebook, Atlas, and plan records
- host repos only stop using local Odylith product docs as the authoritative source

## Test Strategy
- validate the new public component registry against the new product component specs
- keep public pytest green
- repoint downstream repo references and run focused host-repo validation afterward

## Open Questions
- should the public repo later render and commit its own generated surface files, or keep source truth only and generate on demand
- when downstream repos stop carrying local Odylith implementation, which downstream tests should move into Odylith and which should remain host-repo acceptance tests
