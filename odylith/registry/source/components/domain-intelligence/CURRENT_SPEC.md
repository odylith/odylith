# Domain Intelligence
Last updated: 2026-06-03


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
- 2026-05-08: Hardened greenfield traceability writes so applied Radar sections preserve structured risk, question, dependency, rollout, and punctuation semantics instead of splitting governed prose into fragments. Source-local external-domain apply now writes B-001..B-004 with complete risk mitigations, intact open questions, intact dependencies, release-stage rollout lines, and no `R1.`/`Q1.`/split-prose sludge. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-08: Deepened the default greenfield Atlas UX so generated diagram rows carry review focus, operator question, and proof-gate guidance, proposal text explains how to read each Atlas view, and default Mermaid sources include evidence-boundary, code-gate, decision-lens, state-note, unresolved-risk, and surface-agreement annotations directly inside the diagrams. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-08: Hardened greenfield workstream and risk generation against the remaining applied-Radar sludge found in a fresh external-domain audit. Proposal-level risks are now domain-specific structured records, old generic risk boilerplate is rejected, workstream ontology labels must be unique, malformed `owns Own ...` generated prose is rejected, and parent workstreams keep program ontology separate from child implementation nouns. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-184`)
- 2026-05-09: Hardened greenfield child backlog row generation so domain-profiled proposals produce product-requirement workstreams instead of generic B-002/B-003/B-004 shells. Domain profiles now receive family-specific child workstream titles, problem statements, interfaces, and validation gates without forcing one example domain into product-level governance truth. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-05-09: Split the default greenfield proposal UX into staged review gates instead of dumping the deep accepted record. `greenfield propose` now renders interpretation, clarify-before-apply choices, a compact product preview, and an explicit choose-next-action gate; `--format json` and `greenfield create/apply --confirm` retain the deep project, workstream, component, architecture, release, risk, validation, memory, and Tribunal-gated apply contract. The same pass preserved domain-bearing trailing title terms, removed surface-first show/guidance wording, guarded product-repo source truth from stale consumer repair paths, and made standalone Registry rendering prefer source manifest truth over stale runtime snapshots. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-194`)
- 2026-05-09: Tightened greenfield architecture view naming so generated diagram titles are concise view names rather than full prompt-prefixed labels. Generic and robot-swarm profiles now emit titles such as `System Overview`, `First Slice Flow`, and `Telemetry Contract And Data Flow`; slugs and summaries retain project identity. The Tribunal rejects confirmed proposals whose diagram titles repeat the project title prefix. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-195`)
- 2026-05-14: Replaced the v0.1.15 host-authored JSON repair path with an Odylith-owned confirmed create path. `greenfield propose --confirm-intent --format json` now emits the same apply-ready proposal that `greenfield create --confirm` applies, release smoke runs the confirmed create path against a fresh repo, and installed guidance forbids hand-authored proposal repair loops across hosts. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bugs: `CB-173`, `CB-181`)
- 2026-05-19: Tightened the confirmed-intent internal-systems gate so fail-closed create still rejects the exact generic fallback trio while accepting domain-specific systems that own evidence review, such as a race gearbox run evidence review surface. The recurrence is captured under `CB-202`, and the regression tests prove both acceptance and rejection paths. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-05-20: Added the confirmed-completion gate for `greenfield create --confirm`. Confirmed proposals now fill deterministic omissions before writes: project posture, backlog risk/security fields, component interfaces/dependencies/validation/risks, and non-self-invalidating Atlas watch paths. The gate reruns proposal and governed-artifact Tribunals before create applies source truth, so a rich accepted intent produces a full Radar/Registry/Atlas/release/Compass project set instead of stopping on missing derivable fields. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-02: Hardened the post-confirm semantic render path so first-path clauses, component contracts, Atlas labels, runtime JSON, public dashboard prose, Radar workstreams, and Registry component specs reject parser debris, activity-shaped actor names, framework proof scaffolds, bare outcome nouns, coordinated action-verb drift, and component-boundary boilerplate before any confirmed greenfield writes. First-path parsing now lives in `greenfield_first_path_semantics.py`, separate from title normalization, release classification, and slop scanning. The pass keeps the fix provider-free and domain-agnostic, with regression coverage in `test_greenfield_post_confirm_slop_regressions.py`, an 11.67-second confirmed-create E2E run with no slop hits, and rendered browser proof for Radar and Registry behavior. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Decomposed confirmed-intent completion so `greenfield_confirmed_actor_completion.py` owns actor row completion, actor label derivation, generated meta-row rejection, and actor description repair, while `greenfield_confirmed_intent_completion.py` keeps orchestration, core-field completion, system completion, title repair, and product posture. Shared confirmed text helpers now live in `greenfield_confirmed_text.py`, the former parent dropped below the source-size ceiling, and `test_greenfield_confirmed_intent.py` pins the actor phase outside the parent. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-create prewrite gating so `greenfield_confirmed_prewrite_gate.py` owns semantic model completion, proposal/component/spec preflight issue aggregation, the deterministic greenfield Tribunal call, and governed-artifact Tribunal issue collection. `greenfield_confirmed_completion.py` now stays under the 1200-line hard threshold while delegating the quality gate through a focused owner pinned by `test_greenfield_confirmed_repair.py`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-intent internal-system row parsing into `greenfield_confirmed_system_rows.py`. The owner now handles JSON/Markdown role rows, labeled system spans, sentence-system rows, contextual system descriptions, generic scaffold detection, and exported `confirmed_system_name`/`confirmed_system_description` helpers while `greenfield_confirmed_intent.py` stays below the source-size threshold as a parser/validator entrypoint. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split post-confirm semantic drift checks into `greenfield_post_confirm_semantic_drift.py`. The owner now handles contrastive drift terms, semantic repetition clustering, generated-artifact sentence extraction, intent/component signatures, and semantic overlap scoring while `greenfield_post_confirm_completion.py` stays below the source-size threshold as the package orchestration and prewrite-preview gate. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split post-confirm semantic model alignment into `greenfield_post_confirm_semantic_alignment.py` and shared list-row coercion into `greenfield_post_confirm_rows.py`. Semantic model shape, component/workstream/diagram alignment, rendered Registry spec alignment, component ID fallback, and first-release scope checks now sit outside the package completion parent, which stays below the 800-line soft limit. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-intent validation into `greenfield_confirmed_intent_validation.py`. Field thresholds, meta-narration rejection, qualitative gap checks, progression/outcome scoring, and semantic-overlap term extraction now sit outside `greenfield_confirmed_intent.py`, which stays below the 800-line soft limit as the file/JSON/Markdown parser and normalizer. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-completion quality checks into `greenfield_confirmed_completion_quality.py`. Generic text repair detection, sequence repair detection, proof-boundary weakness checks, and bad sentence-tail detection now sit outside `greenfield_confirmed_completion.py`, keeping quality predicates reusable across completion phases. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-completion phrase and label derivation into `greenfield_confirmed_completion_text_model.py`. The owner now handles action/outcome phrasing, workstream sentences, project/component/diagram labels, first-path/proof/state summaries, actor summaries, keyword extraction, and backlog-to-component lexical matching while `greenfield_confirmed_completion.py` stays below the 800-line soft limit and calls component contract owners directly for interfaces, dependencies, and validation defaults. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Tightened `greenfield_confirmed_components.py` by removing a duplicate `_title_phrase` definition and the unused `_can_clause` helper; the confirmed component owner now stays below the 800-line soft limit with structural coverage in `test_greenfield_component_spec_quality.py`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed Radar workstream phrase derivation into `greenfield_confirmed_backlog_text_model.py`. The owner now handles actor labels, first-action/outcome clauses, proof focus selection, problem fallback wording, product-term overlap checks, and rationale-line generation while `greenfield_confirmed_backlog.py` stays below the 800-line soft limit as the program/release/backlog record assembler. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed Atlas diagram text and label derivation into `greenfield_confirmed_diagram_text.py`. The owner now handles component card descriptions, product/actor/proof briefs, proof-review labels, workstream titles, Mermaid label trimming, and short-label cleanup while `greenfield_confirmed_diagrams.py` stays below the 800-line soft limit as the row assembly and flowchart wiring owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split specialized generated Registry component contract profiles into `greenfield_component_contract_profiles.py`. Document-context and status-view contract builders now own their profile-specific phrase extraction, transition selection, outside-boundary wording, and local proof rows while `greenfield_component_contract.py` stays below the 800-line soft limit as the profile selector and generic fallback contract owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split generated Registry component semantic context extraction into `greenfield_component_semantic_context.py`. Context-derived phrase extraction, late first-path/proof backfill selection, context anchor expansion, actor/action prefix removal, and context-backfill decisions now sit outside `greenfield_component_semantic_contract.py`, which stays below the 800-line soft limit as the semantic contract assembly owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split generated Registry component contract target parsing into `greenfield_component_contract_targets.py`. Rendered-spec issue parsing, duplicate repair-target dedupe, and operator-facing component-spec blocker copy now sit outside `greenfield_component_contract_differentiation.py`, which stays below the 800-line soft limit as the contract repair orchestrator. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-create apply-prewrite component and diagram rendering into `greenfield_apply_components.py` and `greenfield_apply_diagrams.py`. First-release Registry input shaping, dry-run component preview, in-memory Registry spec rendering, component dependency/risk/responsibility copy, Atlas source preview, and diagram ID allocation now sit outside `greenfield_apply_prewrite.py`, which stays below the 800-line soft limit as the staged package and remapping owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-create final governed writes into `greenfield_apply_write.py`. The owner now applies Radar source files, stale workstream cleanup, release targeting, program waves, Atlas scaffold/upsert writes, Registry component authoring, accepted-project memory, dashboard refresh, and next-step shaping while `greenfield_proposals.py` stays below the 800-line soft limit as the intent/proposal/prewrite transaction entrypoint. The same pass aligned blank component `release_scope` with the semantic builder and refreshed stale apply semantic models before completion gates run. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split first-path clause rendering into `greenfield_first_path_clauses.py` and shared first-path records into `greenfield_first_path_types.py`. `greenfield_first_path_semantics.py` now owns parsing and semantic model extraction only, while the clause owner renders action, capability, visible-result, action-chain, and trivial-start grammar for Radar, Registry, Atlas, runtime JSON, and dashboard copy. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed generated-artifact substance checks into `proposal_tribunal_substance.py`. The new owner handles confirmed Radar thinness, Registry component-contract substance, cross-axis proof leakage, Atlas scaffold-node rejection, first-path tail preservation, and first-boundary routing while `proposal_tribunal.py` stays focused on deterministic prewrite adjudication and topology/security/actor gates. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-intent internal-system completion into `greenfield_confirmed_system_completion.py`. The owner now completes internal system rows, fallback systems, system labels, state labels, and context-clause matching while `greenfield_confirmed_intent_completion.py` stays focused on orchestration, core fields, product posture, title repair, and first-path/proof wording. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split Atlas first-path event-step derivation into `greenfield_sequence_steps.py`. The step owner now handles semantic events, launcher-only filtering, first-path fallback parsing, compound-step expansion, and dedupe while `greenfield_sequence_diagram.py` stays below the 800-line soft limit as the participant/component routing and Mermaid rendering owner. The pass also preserves final `act later` decision tails and short role-qualified component artifacts such as `person follow list` in confirmed create output. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split Domain Intelligence artifact enrichment so `artifact_graph.py` owns graph normalization and `artifact_tribunal_actors.py` owns visible Tribunal actor projection. `artifact_enrichment.py` now stays below the 800-line soft limit as the artifact projection owner, and project-intelligence callers import graph and actor helpers from their dedicated owners. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed project-brief rendering into `greenfield_confirmed_project_brief.py` and consolidated greenfield command quoting into `greenfield_command_text.py`. `greenfield_confirmed_components.py` now stays below the 800-line soft limit as the confirmed Registry component generator instead of also owning project-readiness copy and host handoff commands. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Consolidated component-contract phrase and term helper ownership in `greenfield_component_terms.py`. Base contracts, semantic contracts, and contract differentiation now reuse `natural_phrase`, `phrase`, and `domain_terms` instead of carrying local `_term_phrase`, `_phrase`, or `_content_terms` clones, while all touched component-contract files stay below the 800-line soft limit. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed component completion into `greenfield_confirmed_component_completion.py`. Component contract normalization, contract-derived responsibility/boundary/interface/dependency/validation/risk repair, component risk enrichment, and component sentence repair now sit outside `greenfield_confirmed_completion.py`, which stays below the 800-line soft limit as the confirmed-create repair orchestrator. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Consolidated generated list-row coercion in `greenfield_rows.py`. Confirmed prewrite gating, the deterministic Tribunal, confirmed title repair, apply-prewrite remapping, confirmed completion, and post-confirm semantic/package checks now import `mapping_rows` or `dict_rows` from the shared owner instead of carrying private `_mapping_rows`/`_dict_rows` clones or a post-confirm-specific wrapper. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Extended shared row coercion to remaining component, backlog, handoff, created-row, proposal-row, and wave-row readers, and hardened semantic context cleanup for confirmed Registry contract text. `greenfield_backlog_impact.py`, `greenfield_experience.py`, `greenfield_confirmed_component_completion.py`, and `greenfield_component_contract_differentiation.py` now reuse `mapping_rows` or `dict_rows`, while `greenfield_component_semantic_context.py` strips metadata-led actor/action phrases and `greenfield_confirmed_project_brief.py` rewrites awkward show-actor-artifact copy before project posture text is rendered. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Consolidated confirmed-intent list text coercion in `greenfield_confirmed_text.py`. The parser, completion, actor-completion, system-completion, and validation owners now call `confirmed_text_values` instead of carrying local `_strings` helpers, so Markdown cleanup and strict accepted-intent list semantics stay in one shared confirmed-text owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)

## Contract

- `greenfield_proposals.py` owns the no-write Product Intent request and the
  confirmed create/apply path. It must not infer final project boundaries from a
  fixed in-code domain list or push private schema repair onto the host.
- `proposal_normalization.py` owns compatibility normalization for reasonable
  host-authored proposal shapes before strict validation. It may repair field
  spelling, release-plan shape, proof-field aliases, generic diagram
  slugs, Mermaid sequence message punctuation, and missing umbrella program
  parents, but it must not invent source-backed implementation evidence.
- `greenfield_transaction.py` owns retry-safe source-truth rollback for failed
  greenfield apply runs. It snapshots the greenfield-owned Radar, Registry,
  Atlas, and Compass acceptance source paths before writes and restores them on
  failure so a retry cannot be blocked by duplicate ideas, stale catalog rows,
  stale component dossiers, or release events from a rejected apply.
- `proposal_rendering.py` owns operator-facing text and apply-command rendering
  so proposal compilation, planning, and presentation stay decoupled.
- Default `greenfield propose` text is a no-write Product Intent Confirmation
  request, not the durable record dump. It must prompt the host to narrate the
  product, user, problem, first workflow, proof boundary, and confirm/edit/reject
  gate before any writes. After confirmation, `greenfield create --confirm`
  builds and applies the durable record; `propose --confirm-intent --format json`
  is the optional review artifact for the same apply-ready object.
- Confirmed-intent parsing must accept both bullet-row and prose-row internal
  systems when the accepted narrative is concrete enough to infer owned product
  systems. Generic scaffold detection may reject exact fallback names together,
  but it must not reject a project-specific `evidence review` system solely
  because evidence review is part of its domain responsibility.
- Confirmed-create completion must run after normalization and before any
  source-truth write. It fills every deterministic Radar, Registry, Atlas,
  release, risk, proof, and validation field derivable from the accepted intent,
  then reruns the greenfield Tribunal and governed artifact Tribunals. It may
  retry bounded deterministic omissions, but it must not invent source-backed
  implementation evidence or ask the host to hand-author proposal JSON.
- Confirmed-create semantic rendering must run after deterministic completion
  and before any source-truth write. It must compile first-path action,
  capability, and visible-result clauses once from the accepted semantic model,
  keep post-result follow-up from leaking into the first implementation slice,
  normalize coordinated action verbs through the shared prose grammar owner, and
  fail closed when generated Radar, Registry, Atlas, project-dashboard, or
  runtime JSON text still contains parser debris, role/action splices, bare
  outcome nouns, generic proof scaffolds, component-boundary boilerplate, or
  unclear human-visible copy.
- First-path parsing must stay in `greenfield_first_path_semantics.py`;
  generated first-path action, capability, visible-result, action-chain,
  trivial-start, and visible-result cleanup grammar must stay in
  `greenfield_first_path_clauses.py`; shared `FirstPathModel` and
  `FirstPathClauses` records must stay in `greenfield_first_path_types.py`.
  Domain Intelligence may reuse those helpers through
  `greenfield_semantic_quality.py`, but it must not reintroduce first-path
  clause rendering into the parser.
- Atlas first-path step derivation must stay in
  `greenfield_sequence_steps.py`. Sequence and flowchart renderers may call
  `sequence_event_steps`, but they must not re-own semantic event extraction,
  launcher-only filtering, fallback first-path splitting, compound-step
  expansion, or step dedupe. First-path scope detection must not classify
  user-decision tails such as `act later` as deferred release scope.
- Generated Registry component artifact cleanup must preserve short
  role-qualified artifact identities when they end in an owned artifact noun,
  for example `person follow list` and `reviewer notes`; it may still strip
  generic actor noise from longer non-artifact prose.
- Component-contract phrase and term helpers must stay in
  `greenfield_component_terms.py`. Base component contracts, semantic
  contracts, and contract differentiation may call `natural_phrase`, `phrase`,
  and `domain_terms`, but they must not reintroduce local `_term_phrase`,
  `_phrase`, or `_content_terms` clones for generated Registry contract text.
- Confirmed component row completion must stay in
  `greenfield_confirmed_component_completion.py`. The confirmed completion
  parent may call `complete_component_rows` and
  `repair_component_sentence_lists`, but it must not re-own component contract
  normalization, contract-derived responsibility/boundary/interface/dependency
  repair, component risk enrichment, component weakness checks, or component
  sentence-list repair.
- Generated list-row coercion must stay in `greenfield_rows.py`. Confirmed
  prewrite gates, Tribunal checks, title repair, apply-prewrite remapping,
  confirmed completion, backlog impact, implementation handoff shaping,
  component completion, component-contract differentiation, and post-confirm
  semantic/package checks may call `mapping_rows`, `dict_rows`, `row_count`, or
  `mapping_count`, but they must not reintroduce local `_mapping_rows`,
  `_dict_rows`, `_component_rows`, `_created_rows`, `_row_count`, or
  `_mapping_count` helpers, package-local count helpers, or a phase-specific
  row wrapper.
- Confirmed semantic context cleanup must remove generated metadata prefixes
  before actor/action trimming, so project-brief, customization, checkpoint, or
  command labels cannot turn accepted proof text into artifact nouns such as
  `resident create repair request`. Project-brief copy must also normalize
  awkward `shows the <actor> a <result>` phrasing before it is written into
  human-visible project posture.
- Confirmed-intent list text coercion must stay in
  `greenfield_confirmed_text.py`. Parser, completion, actor-completion,
  system-completion, and validation modules may call `confirmed_text_values`,
  but they must not reintroduce local `_strings` helpers or silently flatten
  mapping-shaped values into accepted intent list rows.
- Confirmed-intent actor completion must stay in
  `greenfield_confirmed_actor_completion.py`. The parent completion module may
  call `completed_actor_rows`, `actor_labels`, and `actor_row_description`, but
  it must not reintroduce local actor label derivation, generated meta-row
  filtering, or actor description repair.
- Confirmed-intent internal-system row parsing must stay in
  `greenfield_confirmed_system_rows.py`. The confirmed-intent entrypoint may
  call `role_or_system_rows`, `internal_system_rows`,
  `expand_internal_system_rows`, and `contains_generic_system_scaffold`, but it
  must not re-own local labeled-span parsing, sentence-system row splitting,
  system-name prefix detection, or generated system-description repair.
- Confirmed-intent internal-system completion must stay in
  `greenfield_confirmed_system_completion.py`. The confirmed-intent completion
  orchestrator may call `completed_system_rows`, `system_labels`, and
  `state_label`, but it must not re-own fallback system generation, system
  label cleanup, system-description cleanup, or context-clause matching.
- Confirmed-create prewrite gating must stay in
  `greenfield_confirmed_prewrite_gate.py`. The completion orchestrator may call
  `complete_semantic_model` and `preflight_issues`, but it must not re-own the
  greenfield Tribunal call, governed-artifact Tribunal aggregation, or local
  proposal/component/spec issue collector loop.
- Confirmed-create final governed writes must stay in
  `greenfield_apply_write.py`. The greenfield proposal entrypoint may call
  `release_assignment_note` and `write_greenfield_proposal`, but it must not
  re-own Radar source writes, stale workstream cleanup, release assignment
  writes, program wave creation, Atlas scaffold/upsert helpers, Registry
  component authoring, accepted-project memory recording, dashboard refresh, or
  next-step shaping.
- Installed greenfield guidance must not ask Codex or Claude hosts to hand-author
  or reconstruct proposal JSON. Proposal review uses the canonical object from
  `greenfield propose`; confirmation uses `greenfield create --confirm` unless an
  explicit file workflow is needed, in which case the file comes from
  `greenfield propose --format json`.
- `proposal_validation.py` owns confirmed proposal validation, required
  Mermaid source checks, evidence-tier checks, and duplicate-topology rejection.
  Generic Atlas scaffold remains the low-level catalog/source writer; Domain
  Intelligence validates proposal topology instead of inventing source-backed
  implementation evidence.
- `proposal_tribunal.py` owns deterministic pre-write adjudication. It fails
  proposals whose child workstreams lack component/diagram/dependency/proof
  topology, whose components lack boundary/interface/dependency/proof
  expectations, whose diagrams do not connect to backlog and Registry
  components, or whose release/program structure cannot make Compass visibly
  useful.
- Confirmed generated-artifact substance checks must stay in
  `proposal_tribunal_substance.py`. `proposal_tribunal.py` may call
  `check_confirmed_artifact_substance`, but it must not re-own confirmed Radar
  thinness checks, Registry local-proof leakage checks, Atlas scaffold-node
  rejection, first-path tail preservation, first-boundary routing, or the
  project-term analysis used to judge generated artifact specificity.
- Artifact enrichment must keep workstream graph normalization and visible
  Tribunal actor naming in dedicated owners. `artifact_enrichment.py` may call
  `artifact_graph.domain_graph_from_workstream` and
  `artifact_tribunal_actors.tribunal_actor_projection`, but it must not re-own
  `DomainIntelligenceGraph`, state-object/actor/approval row selection, domain
  actor naming, proposal actor candidate selection, or visible actor dedupe.
- Confirmed project-brief generation and greenfield command quoting must stay
  outside the confirmed component generator. `greenfield_confirmed_components.py`
  may build Registry component rows and component labels, but it must not
  re-own `confirmed_project_brief`, project-readiness gates, host-independent
  path text, or a local `shell_quote` helper. Command quoting belongs in
  `greenfield_command_text.py`.
- Apply-ready proposal output must include observed source posture, user intent,
  Odylith assumptions, backlog candidates, program formation, program waves,
  release plan, planned Registry components, proposal draft Atlas Mermaid sources,
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
- Greenfield child backlog rows must be product-requirement rows derived from
  the inferred domain profile before Domain Intelligence enrichment runs. A
  project-specific prompt must not inherit unrelated default vocabulary from an
  integration token or example domain; it must preserve the actual beneficiary,
  state object, risk model, proof obligations, and release boundary instead.
- Consumer legacy repair for misclassified greenfield records is consumer-lane
  only. It must no-op in the Odylith product repo even when the product repo
  contains historical bug, plan, or test fixtures with matching poison tokens.
- Greenfield workstream Domain Intelligence must remain bespoke and
  non-repetitive. Ontology labels are unique inside each workstream; umbrella
  workstreams use program/control-surface vocabulary rather than repeating child
  implementation terms; generated ownership prose must not contain malformed
  phrases such as `owns Own ...`.
- Greenfield proposal risks must be domain-specific risk records, not copied
  boilerplate. The accepted risk shape preserves risk class, severity, trigger,
  early-warning signal, and mitigation through proposal text and applied Radar
  source so future agents can act on the risk rather than reread generic prose.
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
- `tests/unit/runtime/test_greenfield_confirmed_intent.py`
- `tests/unit/runtime/test_greenfield_confirmed_repair.py`
- `tests/unit/runtime/test_greenfield_row_coercion.py`
- `tests/unit/runtime/test_greenfield_host_routing.py`
- `tests/unit/runtime/test_greenfield_intelligence_schema.py`
- `tests/unit/runtime/test_greenfield_atlas_contract.py`
- `tests/unit/runtime/test_tribunal_engine.py`
- `tests/unit/test_cli.py`
- `tests/unit/runtime/test_component_authoring.py`
- `tests/unit/runtime/test_program_wave_authoring.py`
- `tests/unit/runtime/test_execution_wave_view_model.py`
- `tests/unit/runtime/test_execution_wave_ui_runtime_primitives.py`
- `tests/integration/runtime/test_surface_browser_smoke.py`
- `tests/integration/runtime/test_compass_browser_regression_matrix.py`
- `tests/unit/runtime/test_compass_transaction_runtime.py`
