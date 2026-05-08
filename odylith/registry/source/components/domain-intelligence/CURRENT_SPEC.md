# Domain Intelligence
Last updated: 2026-05-08


## Overview

Domain Intelligence is the host-reasoning contract and confirmation-gated apply
runtime for greenfield consumer governance. It gives every supported host a
strict evidence/schema/validation contract, then writes accepted
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
- **2026-05-07 · Implementation:** Deepened B-142 greenfield Atlas output: generic scaffolds now emit five architecture views and the robot-swarm logistics profile emits ten domain-specific diagrams, tracked by CB-182.
  - Scope: B-142
  - Evidence: odylith/casebook/bugs/2026-05-08-greenfield-atlas-proposal-suite-is-too-shallow-for-architecture-review.md, src/odylith/runtime/domain_intelligence/proposal_scaffold.py +2 more
- **2026-05-06 · Implementation:** Hardened greenfield Tribunal/apply rollback and refreshed generated governance surfaces after migration, CLI, and headless-browser QA.
  - Scope: B-142
  - Evidence: src/odylith/runtime/domain_intelligence/greenfield_transaction.py, tests/unit/runtime/test_greenfield_proposals.py
- **2026-05-06 · Implementation:** Hardened greenfield engine alignment: exact code-path context now carries Registry owner into the Execution Engine handshake, greenfield proposal requests expose all activation layers, CB-174 captured, and sync check-only passes after Registry/Atlas refresh.
  - Evidence: odylith/casebook/bugs/2026-05-06-context-exact-code-paths-lose-registry-owner-in-execution-handshake.md, src/odylith/runtime/context_engine/odylith_context_engine_projection_entity_runtime.py +1 more
- **2026-05-02 · Implementation:** Replaced Domain Intelligence template catalog path with host-reasoned proposal contract, apply-time schema validation, and host-authored Atlas Mermaid source requirements; reran engine, migration, and browser proof.
  - Scope: B-142
  - Evidence: odylith/registry/source/components/domain-intelligence/CURRENT_SPEC.md, src/odylith/runtime/domain_intelligence/greenfield_proposals.py +1 more
- **2026-05-02 · Implementation:** Domain Intelligence corrected to host-reasoned proposal authoring with apply-time topology validation and no in-code project taxonomy.
  - Scope: B-142
  - Evidence: odylith/radar/source/ideas/2026-05/2026-05-03-universal-greenfield-domain-intelligence.md, src/odylith/runtime/domain_intelligence/greenfield_proposals.py +1 more
- **2026-05-02 · Implementation:** Hardened B-142 Domain Intelligence with alternate-fit classification, acronym-safe titles, dedicated proposal rendering, program-formation output, migration-observer markers, full engine/install/browser proof, and fresh empty-consumer apply proof.
  - Scope: B-142
  - Evidence: src/odylith/runtime/domain_intelligence/archetypes.py, src/odylith/runtime/domain_intelligence/greenfield_proposals.py +2 more
<!-- registry-requirements:end -->

## Feature History

- 2026-05-03: Replaced the v0.1.13 in-code project-taxonomy path with a host-reasoning evidence/schema contract because a small checked-in catalog cannot cover open-world user intent. The CLI now supplies repo evidence and guardrails; the host model authors the concrete proposal; Odylith validates and applies after confirmation. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Added `proposal_validation.py` so greenfield apply requires host-authored Mermaid topology per diagram and rejects missing or duplicated diagram source before any Radar, Registry, Atlas, release, or Compass write. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Registered `domain-intelligence` through `odylith component register` and linked it to B-142/D-043 as the first-class owner for universal greenfield proposal intelligence. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Deleted the in-code taxonomy and proposal-planning modules from the active proposal-authoring path. The active host model now owns project-specific reasoning; Odylith owns source posture, evidence tiers, schema validation, apply safety, and durable memory. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Added `proposal_rendering.py` so operator-facing text and apply commands have a focused owner without encoding canned narration or project templates. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-03: Retargeted the greenfield lane to v0.1.14 and made the proposal/apply path show release and program power by default: omitted release selectors become `0.0.1`, child workstreams form an umbrella execution-wave program, and the umbrella plus first wave target the first release while later waves remain visible future work. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-04: Hardened greenfield apply so proposed waves are never silently dropped when token overlap fails; every accepted program wave remains visible, with deterministic fallback child assignment preserving operator-authored structure for follow-up refinement. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-167`)
- 2026-05-05: Added the deterministic greenfield proposal Tribunal and collapsed apply-time visibility into one final batched Radar/Registry/Atlas/Compass refresh after all accepted artifacts and Compass memory are written. The gate is host-model agnostic: hosts author proposal content, while Odylith adjudicates topology, component ownership quality, release targeting, wave focus, and surface visibility before source truth changes. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-06: Hardened greenfield apply against loose host-authored proposal JSON and failed retry poison: common field shapes normalize before validation, generic diagram slugs are project-scoped, diagram traceability accepts workstream IDs as well as titles, sequence labels normalize parser-sensitive semicolons, and failed apply rolls back greenfield source truth instead of leaving duplicate Radar, Registry, Atlas, release, or Compass acceptance state. The proposal request contract now also requires domain-proportional security, privacy, compliance, abuse, accessibility, data-retention, and operational risk posture. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-173`)
- 2026-05-07: Hardened the release-blocking greenfield path found in CRISPR Ethics manual testing: proposals that omit a true umbrella now synthesize `Govern <Project>` before validation, wave/release/traceability mapping resolves proposal-local `WS-*` IDs to created `B-*` IDs, nested security/compliance posture is flattened into readable bullets instead of raw list literals, component specs now include implementation kickoff guidance, and apply output names the first child workstream plus validation commands. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-176`)
- 2026-05-07: Made provider-free greenfield proposals apply-ready by construction: `greenfield propose --format json` emits the canonical proposal object that `greenfield apply` consumes, `greenfield create --confirm` owns the one-command confirmed path, batch validation reports complete remediation issues, the human proposal renders from the same object, and the robot-swarm logistics specialization now lives in a focused profile owner instead of the generic scaffold assembler. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bugs: `CB-173`, `CB-176`, `CB-181`)
- 2026-05-07: Aligned installed and bundled greenfield host guidance with the apply-ready contract: AGENTS, README, `odylith-greenfield-governance`, and `odylith-show-me` now route confirmation to `greenfield create --confirm`, forbid hand-authored proposal JSON, and are pinned by source plus release-smoke guidance tests. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bugs: `CB-176`, `CB-181`)
- 2026-05-08: Deepened greenfield Atlas architecture output so the provider-free default scaffold now emits five views (system overview, first-slice flow, component ownership, domain state, validation/release topology) and the robot-swarm logistics profile emits ten views by adding conflict, safety/e-stop, telemetry contract, deployment-boundary, and observability/audit diagrams. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-182`)
- 2026-05-08: Deepened greenfield Radar workstreams from task labels into domain-intelligence control surfaces. Each applied workstream now carries structured intent, ontology, state, operators, constraints, source-of-truth hierarchy, evidence grammar, decisions, assumptions, topology, invariants, risks, validation obligations, artifact contracts, authority, execution memory, metrics, change rules, conflict rules, and transfer priors; proposal preview, normalization, validation, Radar writes, and traceability repair all share the same payload. `greenfield apply/create --json` now captures noisy internal refresh/scaffold output and emits one parseable JSON document. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bugs: `CB-184`, `CB-185`)
- 2026-05-08: Made greenfield project-first before implementation: canonical proposals now include a top-level `project_brief` with blueprint sections, customization options, pre-coding checkpoints, coding-readiness gates, and host-independent commands. Validation rejects missing briefs, legacy proposals normalize into the same shape, rendered proposals show the brief before backlog, and apply/create closeout leads with the project workstream before the eventual coding lane. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-186`)
- 2026-05-08: Tightened greenfield Registry candidate specs so component dossiers stay component-owned rather than project-summary repeats. Apply now keeps proposal-wide security/compliance/risk posture in the project brief and Radar, writes component-local failure/security/policy guardrails, extracts boundary exclusions into `Outside Boundary`, and chooses the most specific child workstream as each component's implementation anchor. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-187`)
- 2026-05-08: Hardened greenfield traceability writes so applied Radar sections preserve structured risk, question, dependency, rollout, and punctuation semantics instead of splitting governed prose into fragments. Source-local DeFi apply now writes B-001..B-004 with complete risk mitigations, intact open questions, intact dependencies, release-stage rollout lines, and no `R1.`/`Q1.`/split-prose sludge. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-08: Deepened the default greenfield Atlas UX so generated diagram rows carry review focus, operator question, and proof-gate guidance, proposal text explains how to read each Atlas view, and default Mermaid sources include evidence-boundary, code-gate, decision-lens, state-note, unresolved-risk, and surface-agreement annotations directly inside the diagrams. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))

## Contract

- `greenfield_proposals.py` owns the host-reasoning request contract and the
  confirmed apply path. It must not infer final project boundaries from a fixed
  in-code domain list.
- `proposal_normalization.py` owns compatibility normalization for reasonable
  host-authored proposal shapes before strict validation. It may repair field
  spelling, release-plan shape, component proof-field aliases, generic diagram
  slugs, Mermaid sequence message punctuation, and missing umbrella program
  parents, but it must not invent source-backed implementation evidence.
- `greenfield_transaction.py` owns retry-safe source-truth rollback for failed
  greenfield apply runs. It snapshots the greenfield-owned Radar, Registry,
  Atlas, and Compass acceptance source paths before writes and restores them on
  failure so a retry cannot be blocked by duplicate ideas, stale catalog rows,
  stale component dossiers, or release events from a rejected apply.
- `proposal_rendering.py` owns operator-facing text and apply-command rendering
  so proposal compilation, planning, and presentation stay decoupled.
- Installed greenfield guidance must not ask Codex or Claude hosts to hand-author
  or reconstruct proposal JSON. Proposal review uses the canonical object from
  `greenfield propose`; confirmation uses `greenfield create --confirm` unless an
  explicit file workflow is needed, in which case the file comes from
  `greenfield propose --format json`.
- `proposal_validation.py` owns host-reasoned proposal validation, required
  Mermaid source checks, evidence-tier checks, and duplicate-topology rejection.
  Generic Atlas scaffold remains the low-level catalog/source writer; Domain
  Intelligence validates host-authored topology instead of inventing it.
- `proposal_tribunal.py` owns deterministic pre-write adjudication. It fails
  proposals whose child workstreams lack component/diagram/dependency/proof
  topology, whose components lack boundary/interface/dependency/proof
  expectations, whose diagrams do not connect to backlog and Registry
  components, or whose release/program structure cannot make Compass visibly
  useful.
- Host-reasoned proposal output must include observed source posture, user
  intent, Odylith assumptions, backlog candidates, program formation, program
  waves, release plan, planned Registry components, host-authored draft Atlas
  Mermaid sources,
  validation strategy, risks, open questions, exact apply commands, and
  domain-proportional security, privacy, compliance, abuse, accessibility,
  data-retention, and operational risk posture.
- Greenfield backlog rows must carry structured `domain_intelligence` before
  validation and apply. The payload is not decorative prose: it must encode the
  workstream as a domain control surface with project-specific vocabulary,
  allowed operations, state transitions, source-of-truth map, evidence model,
  topology, invariants, risks, validation obligations, execution memory,
  change/invalidation rules, conflict rules, and reusable priors. Normalization
  may enrich legacy proposals, but apply must reject rows that remain shallow.
- Greenfield proposals must carry a top-level `project_brief` before validation
  and apply. The brief owns the project-first UX contract: blueprint sections,
  direction/customization options, pre-coding checkpoints, coding-readiness
  gates, and host-independent commands that work the same from CLI, Codex, and
  Claude Code. Apply creates governed project truth; it must not imply coding
  should start until those gates are accepted or explicitly waived.
- Radar workstream authoring must preserve the `Domain Intelligence` section in
  source workstream files, and traceability repair must reapply that section if
  later greenfield topology patching rewrites the same file.
- `greenfield apply --json` and `greenfield create --json` must keep stdout
  machine-clean. Internal progress from refresh, scaffold, or renderer helpers
  may be captured into the JSON payload, but it must not precede or follow the
  JSON document on stdout.
- Provider-free default scaffolds must produce a multi-view Atlas architecture
  suite before apply: topology, first-slice sequence, component ownership,
  state/data contract, and validation/release topology. Domain-specific
  profiles may add more diagrams when the prompt reveals material architecture
  risk, such as robot swarm conflict, safety, telemetry, deployment, and audit
  views.
- If the operator does not provide a release target for a greenfield proposal,
  the default first release selector is `0.0.1`, not an Odylith product-version
  alias such as `next`. Accepted proposals with child workstreams should create
  an umbrella execution-wave program and target the umbrella plus first wave to
  the first release so Compass can show program/wave/release structure without
  pretending every future child is ready for the first release.
- Apply must preserve all host-authored program waves. A weak or missing
  token-overlap match may choose a deterministic fallback child, but it must not
  erase the wave or report success with fewer waves than the accepted proposal.
- Apply must resolve proposal-local workstream identifiers such as `WS-01` and
  `WS-IDENTITY-ACCESS` when assigning execution waves, release targets, and
  traceability. The first child workstream must not become the program parent
  simply because the host omitted a `WS-00` umbrella row.
- Apply output must hand off the project first, not just artifact counts: it
  names the program parent, project brief deep link, direction choices,
  coding-readiness gates, active wave, release target, eventual first child
  workstream, first validation gates, and verification commands the operator
  should run before moving to code or the next wave.
- Greenfield apply must generate an implementation runway, not a governance
  dead end. The runway includes a first child workstream, first active wave,
  release target, first coding slice, definition of done, operator sequence, and
  verification commands. The umbrella parent remains program context and must
  not become the first component kickoff anchor.
- Execution-wave source must preserve accepted proposal exit gates and
  validation text so Compass and Radar can render what closes a wave instead of
  only showing membership counts.
- Candidate component specs created from greenfield proposals are component
  dossiers, not project summaries. Project-level posture belongs in the
  project brief and Radar; each Registry spec must stay scoped to that
  component's own boundary, outside-boundary exclusions, collaborators,
  interfaces, failure modes, proof obligations, first source path, and most
  specific child workstream anchor.
- Apply must run the greenfield Tribunal before any governed write and must
  perform one final batched dashboard refresh for Radar, Registry, Atlas, and
  Compass after backlog, program, release, Atlas, Registry, and Compass memory
  records are written. Do not insert per-artifact refreshes that slow the happy
  path or expose partial generated surfaces.
- Apply failures after the pre-write Tribunal must restore the greenfield-owned
  source truth paths before returning an error. Operators must not be asked to
  hand-delete partial Radar ideas, Registry dossiers, Atlas catalog/source, or
  release assignment artifacts before retrying the same confirmed proposal.
- `Customer` may be a one-token governed value. Problem, Opportunity, Product
  View, and Success Metrics keep the stronger detail and placeholder-rejection
  rules.
- Default CLI proposal request generation must not call providers directly; the
  active host model supplies the reasoning in host sessions.
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
- `tests/unit/runtime/test_tribunal_engine.py`
- `tests/unit/test_cli.py`
- `tests/unit/runtime/test_component_authoring.py`
- `tests/unit/runtime/test_program_wave_authoring.py`
- `tests/unit/runtime/test_execution_wave_view_model.py`
- `tests/unit/runtime/test_execution_wave_ui_runtime_primitives.py`
- `tests/integration/runtime/test_surface_browser_smoke.py`
- `tests/integration/runtime/test_compass_browser_regression_matrix.py`
- `tests/unit/runtime/test_compass_transaction_runtime.py`
