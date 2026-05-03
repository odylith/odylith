# Domain Intelligence
Last updated: 2026-05-02


## Overview

Domain Intelligence is the provider-free runtime that turns greenfield consumer
intent into confirmation-gated Odylith governance proposals. It is the owner
for project archetype selection, program-wave planning, provisional release
planning, proposed component maps, draft Atlas topology, assumptions, risks,
validation obligations, and apply commands for empty or thin repos.

## Boundary

- **Logical boundary**: deterministic domain-intent compilation for greenfield
  consumer-lane proposals.
- **Evidence anchor**: `src/odylith/runtime/domain_intelligence`
- **Kind**: library
- **Status**: active
- **Evidence tier**: manifest
- **Workstreams**: B-141, B-142
- **Diagrams**: D-043

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-05-02 · Implementation:** Deepened B-142 Domain Intelligence with first-class science/math archetypes, greenfield UX/release planning module, refreshed governance surfaces, and full engine/install/browser proof.
  - Scope: B-142
  - Evidence: odylith/radar/source/ideas/2026-05/2026-05-03-universal-greenfield-domain-intelligence.md, src/odylith/runtime/domain_intelligence/archetypes.py +1 more
<!-- registry-requirements:end -->

## Feature History

- 2026-05-03: Registered `domain-intelligence` through `odylith component register` and linked it to B-142/D-043 as the first-class owner for universal greenfield proposal intelligence. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Expanded the catalog with first-class science/math subdomains: formal proof, computational notebooks, numerical simulation, scientific pipelines, geospatial/environmental analysis, ML experiment platforms, and math education. Split program/release/UX planning into `proposal_planning.py` so the proposal compiler stays below the soft source size line while keeping host behavior identical. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Added deterministic fit explainability, alternate archetype candidates, acronym-safe project titles, domain-specific first-slice validation language, and `proposal_rendering.py` so operator-facing text and apply commands have a focused owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))

## Contract

- `archetypes.py` owns the extensible project-domain catalog. New domains are
  added there as structured archetypes, not as host-specific prompt hacks.
- `proposal_planning.py` owns reusable program-wave, release-plan, and
  greenfield UX compilation, including parent/child workstream strategy and
  wave-to-workstream release policy.
- `proposal_rendering.py` owns operator-facing text and apply-command rendering
  so proposal compilation, planning, and presentation stay decoupled.
- `greenfield_proposals.py` owns proposal compilation and confirmed apply.
- Proposal output must include classification fit, observed source posture, user
  intent, Odylith assumptions, backlog candidates, program formation, program
  waves, release plan, planned Registry components, draft Atlas diagrams,
  validation strategy, risks, open questions, and exact apply commands.
- Default proposal generation must not call providers or host models.
- Apply must require `--confirm` and write only through owned Radar, Registry,
  Atlas, and release-targeting paths.

## Research Basis

The v0.1.13 catalog is intentionally broader than a web-app starter. It follows
current public ecosystem shapes: high-volume application and AI/data project
creation, cloud-native platform categories, mature open-source project families
across data/cloud/search/libraries/geospatial/IoT, and science software that
depends on datasets, analysis pipelines, simulations, reproducible notebooks,
visualization, and sustained numerical libraries. The catalog should grow by
adding structured archetypes and validation obligations, not by adding host
prompt text.

The science/math family must stay specific: formal proof proposals use proof
checker and theorem-review obligations, numerical simulation uses unit,
tolerance, and convergence obligations, notebooks use clean execution and
statistical-assumption obligations, geospatial analysis uses CRS/extent/temporal
coverage obligations, ML experiment platforms use dataset lineage and promotion
gates, and math education uses exercise, progression, accessibility, and
human-reviewed mathematical-truth obligations.

## Dependencies

- Upstream: Analysis Engine repo-source posture, user prompt intent, and the
  host routing surfaces that detect greenfield prompts.
- Downstream: Radar backlog authoring, Registry component authoring, Atlas
  scaffold, Compass release/timeline surfaces, and Intervention Engine
  visibility routing.

## Test Coverage

- `tests/unit/runtime/test_greenfield_proposals.py`
- `tests/unit/runtime/test_greenfield_host_routing.py`
- `tests/unit/test_cli.py`
- `tests/unit/runtime/test_component_authoring.py`
- `tests/unit/runtime/test_compass_transaction_runtime.py`
