# Domain Intelligence
Last updated: 2026-05-03


## Overview

Domain Intelligence is the host-reasoning contract and confirmation-gated apply
runtime for greenfield consumer governance. It gives Claude, Codex, and future
hosts a strict evidence/schema/validation contract, then writes accepted
backlog, Registry, Atlas, release, Compass, assumptions, risks, and validation
records only after explicit confirmation.

## Boundary

- **Logical boundary**: host-reasoned greenfield proposal validation and apply.
- **Evidence anchor**: `src/odylith/runtime/domain_intelligence`
- **Kind**: library
- **Status**: active
- **Evidence tier**: manifest
- **Workstreams**: B-141, B-142
- **Diagrams**: D-043

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-05-02 · Implementation:** Replaced Domain Intelligence template catalog path with host-reasoned proposal contract, apply-time schema validation, and host-authored Atlas Mermaid source requirements; reran engine, migration, and browser proof.
  - Scope: B-142
  - Evidence: odylith/registry/source/components/domain-intelligence/CURRENT_SPEC.md, src/odylith/runtime/domain_intelligence/greenfield_proposals.py +1 more
- **2026-05-02 · Implementation:** Domain Intelligence corrected to host-reasoned proposal authoring with apply-time topology validation and no in-code project taxonomy.
  - Scope: B-142
  - Evidence: odylith/radar/source/ideas/2026-05/2026-05-03-universal-greenfield-domain-intelligence.md, src/odylith/runtime/domain_intelligence/greenfield_proposals.py +1 more
- **2026-05-02 · Implementation:** Hardened B-142 Domain Intelligence with alternate-fit classification, acronym-safe titles, dedicated proposal rendering, program-formation output, migration-observer markers, full engine/install/browser proof, and fresh empty-consumer apply proof.
  - Scope: B-142
  - Evidence: src/odylith/runtime/domain_intelligence/archetypes.py, src/odylith/runtime/domain_intelligence/greenfield_proposals.py +2 more
- **2026-05-02 · Implementation:** Deepened B-142 Domain Intelligence with first-class science/math archetypes, greenfield UX/release planning module, refreshed governance surfaces, and full engine/install/browser proof.
  - Scope: B-142
  - Evidence: odylith/radar/source/ideas/2026-05/2026-05-03-universal-greenfield-domain-intelligence.md, src/odylith/runtime/domain_intelligence/archetypes.py +1 more
<!-- registry-requirements:end -->

## Feature History

- 2026-05-03: Replaced the v0.1.13 in-code project-taxonomy path with a host-reasoning evidence/schema contract because a small checked-in catalog cannot cover open-world user intent. The CLI now supplies repo evidence and guardrails; the host model authors the concrete proposal; Odylith validates and applies after confirmation. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Added `proposal_validation.py` so greenfield apply requires host-authored Mermaid topology per diagram and rejects missing or duplicated diagram source before any Radar, Registry, Atlas, release, or Compass write. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Registered `domain-intelligence` through `odylith component register` and linked it to B-142/D-043 as the first-class owner for universal greenfield proposal intelligence. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Deleted the in-code taxonomy and proposal-planning modules from the active proposal-authoring path. The active host model now owns project-specific reasoning; Odylith owns source posture, evidence tiers, schema validation, apply safety, and durable memory. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Added `proposal_rendering.py` so operator-facing text and apply commands have a focused owner without encoding canned narration or project templates. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Retargeted the greenfield lane to v0.1.14 and made the proposal/apply path show release and program power by default: omitted release selectors become `0.0.1`, child workstreams form an umbrella execution-wave program, and the umbrella plus first wave target the first release while later waves remain visible future work. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))

## Contract

- `greenfield_proposals.py` owns the host-reasoning request contract and the
  confirmed apply path. It must not infer final project boundaries from a fixed
  in-code domain list.
- `proposal_rendering.py` owns operator-facing text and apply-command rendering
  so proposal compilation, planning, and presentation stay decoupled.
- `proposal_validation.py` owns host-reasoned proposal validation, required
  Mermaid source checks, evidence-tier checks, and duplicate-topology rejection.
  Generic Atlas scaffold remains the low-level catalog/source writer; Domain
  Intelligence validates host-authored topology instead of inventing it.
- Host-reasoned proposal output must include observed source posture, user
  intent, Odylith assumptions, backlog candidates, program formation, program
  waves, release plan, planned Registry components, host-authored draft Atlas
  Mermaid sources,
  validation strategy, risks, open questions, and exact apply commands.
- If the operator does not provide a release target for a greenfield proposal,
  the default first release selector is `0.0.1`, not an Odylith product-version
  alias such as `next`. Accepted proposals with child workstreams should create
  an umbrella execution-wave program and target the umbrella plus first wave to
  the first release so Compass can show program/wave/release structure without
  pretending every future child is ready for the first release.
- `Customer` may be a one-token governed value. Problem, Opportunity, Product
  View, and Success Metrics keep the stronger detail and placeholder-rejection
  rules.
- Default CLI proposal request generation must not call providers directly; the
  active host model supplies the reasoning in Claude/Codex sessions.
- Apply must require `--confirm` and write only through owned Radar, Registry,
  Atlas, and release-targeting paths.

## Research Basis

The v0.1.14 runtime deliberately avoids a hardcoded domain catalog as the
proposal author. User requests can span any product, science, math, research,
art, policy, infrastructure, or mixed project shape. Until Odylith has a real
marketplace or collectively curated domain catalog, the right architecture is
host-reasoned authorship plus Odylith validation. The host model reasons from
the actual prompt and repo evidence; Odylith enforces evidence tiers,
confirmation gates, topology requirements, apply schema, and durable memory.

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
