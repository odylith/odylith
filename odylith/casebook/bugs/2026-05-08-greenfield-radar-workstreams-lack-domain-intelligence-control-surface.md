- Bug ID: CB-184

- Status: FixedPendingRelease

- Created: 2026-05-08

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: Greenfield Radar workstreams lack domain-intelligence control surface

- Impact: Fresh greenfield apply can create thin Radar workstreams that read like task labels, forcing host agents to rediscover domain vocabulary, state, operators, evidence, risks, and validation before implementation.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Odylith product repo maintainer lane and v0.1.15 consumer greenfield install path, 2026-05-08.

- Detected By: Operator transcript for DeFi Risk Sentinel App greenfield flow plus direct review of generated workstream quality.

- Failure Signature: greenfield create accepted and applied a proposal whose child Radar records were limited to generic Problem/Customer/Opportunity/Product View/Success Metrics sections and lacked structured ontology, state, operators, source-of-truth hierarchy, evidence model, validation obligations, change rules, conflict rules, and execution memory.

- Trigger Path: odylith greenfield propose/create --prompt 'DeFi risk sentinel app' --release 0.0.1 --confirm, then inspect B-002/B-003 Radar workstream specs and subsequent technical-plan kickoff.

- Ownership: Greenfield proposal scaffold, proposal normalization, proposal validation, greenfield traceability patching, and Radar backlog authoring/rendering.

- Timeline: Captured 2026-05-08 through `odylith bug capture`.

- Solution: Added a greenfield workstream intelligence runtime that enriches every backlog row with a structured, project-specific Domain Intelligence payload before validation/apply. Proposal normalization now auto-enriches legacy host proposals, proposal validation rejects rows without the intelligence layers, greenfield traceability writes a `## Domain Intelligence` section into Radar source specs, and backlog authoring preserves extra rendered sections for Radar detail pages. Follow-up anti-slop hardening now rejects old generic greenfield risk boilerplate, carries structured risk class/severity/trigger/early-warning/mitigation fields into proposal and Radar rendering, deduplicates ontology labels inside each workstream, separates umbrella program ontology from child implementation nouns, and rejects malformed generated ownership prose such as `owns Own ...`.

- Blast Radius: Consumer greenfield Radar, Registry kickoff quality, Atlas traceability context, Compass handoff, host-agent technical planning, and regulated-domain first-slice validation.

- SLO/SLA Impact: Release-quality greenfield handoff regresses because agents spend follow-up turns reconstructing domain reality instead of starting from governed project truth.

- Data Risk: No direct data loss; governance truth can under-model sensitive financial, regulated, or safety-relevant data constraints before source implementation.

- Security/Compliance: Security/compliance posture is weakened when regulated prompts do not preserve non-custody, no-live-network, audit, privacy, evidence, and approval boundaries in workstream truth.

- Invariant Violated: Every confirmed greenfield workstream must be a domain-intelligent control surface: intent, ontology, state, operators, constraints, truth map, evidence, decisions, assumptions, topology, invariants, risks, validation, artifacts, authority, memory, metrics, change rules, conflict rules, and transfer priors must be present before source work starts.

- Code References: `src/odylith/runtime/domain_intelligence/greenfield_workstream_intelligence.py`, `src/odylith/runtime/domain_intelligence/proposal_scaffold.py`, `src/odylith/runtime/domain_intelligence/proposal_normalization.py`, `src/odylith/runtime/domain_intelligence/proposal_validation.py`, `src/odylith/runtime/domain_intelligence/greenfield_traceability.py`, `src/odylith/runtime/domain_intelligence/greenfield_proposals.py`, `src/odylith/runtime/governance/backlog_authoring.py`, `src/odylith/runtime/domain_intelligence/proposal_rendering.py`

- Regression Tests Added: `tests/unit/runtime/test_greenfield_proposals.py::test_defi_greenfield_workstreams_capture_domain_intelligence`, `tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_writes_domain_intelligence_into_radar_specs`, `tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_normalization_enriches_legacy_proposals_with_domain_intelligence`, `tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_validation_rejects_old_generic_risk_boilerplate`, `tests/unit/runtime/test_greenfield_intelligence_schema.py::test_workstream_intelligence_captures_scope_owners_and_invalidation_rules`

- Verification: `PYTHONPATH=src pytest -q tests/unit/runtime/test_backlog_authoring.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_backlog_ui_payload_runtime.py tests/unit/runtime/test_backlog_render_support.py tests/unit/runtime/test_build_traceability_graph.py tests/unit/runtime/test_greenfield_host_routing.py tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_greenfield_atlas_contract.py` passed (`136 passed`). Follow-up proof: `python3 -m pytest tests/unit/runtime/test_greenfield_atlas_contract.py tests/unit/runtime/test_greenfield_host_routing.py tests/unit/runtime/test_greenfield_intelligence_schema.py tests/unit/runtime/test_greenfield_proposals.py -q` passed (`49 passed`); source-local `greenfield propose/create` for `DeFi risk sentinel app` produced 4 workstreams, 3 components, 5 diagrams, 27 domain-intelligence fields per workstream, unique ontology labels, project-gated closeout, no old risk boilerplate, no malformed ownership phrase, and component-specific Registry dossiers for Risk Console, Risk Signal Engine, and Scenario Replay Harness.
