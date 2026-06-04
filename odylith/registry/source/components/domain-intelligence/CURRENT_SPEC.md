# Domain Intelligence
Last updated: 2026-06-04


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
- **2026-06-04 · Implementation:** Routed confirmed focus-label title token extraction through shared greenfield label terms so hyphenated generated titles such as Source-backed Review Workspace preserve their visible product signal.
  - Scope: B-142
  - Evidence: src/odylith/runtime/domain_intelligence/greenfield_confirmed_text.py, src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py +1 more
- **2026-06-04 · Implementation:** Routed canonical confirmed project-title repair acceptance checks through shared greenfield label terms so slash-separated title candidates such as AI/ML Review Workspace preserve their visible product signal.
  - Scope: B-142
  - Evidence: src/odylith/runtime/domain_intelligence/greenfield_confirmed_title_repair.py, src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py +1 more
- **2026-06-04 · Implementation:** Routed confirmed-intent title repair and system-label qualifier display tokens through shared greenfield label terms so slash-separated labels such as AI/ML review record preserve their visible product signal.
  - Scope: B-142
  - Evidence: src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_completion.py, src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py +1 more
- **2026-06-04 · Implementation:** Routed Registry artifact cleanup action-token checks through shared greenfield visible words and preserved slash-separated visible-result artifact phrases.
  - Scope: B-142
  - Evidence: src/odylith/runtime/domain_intelligence/greenfield_component_terms.py, src/odylith/runtime/domain_intelligence/greenfield_text.py +1 more
- **2026-06-04 · Implementation:** Routed confirmed component kind-token extraction through shared greenfield visible words so client, adapter, and service classification no longer carries a local regex token loop.
  - Scope: B-142
  - Evidence: src/odylith/runtime/domain_intelligence/greenfield_confirmed_components.py, src/odylith/runtime/domain_intelligence/greenfield_text.py +1 more
- **2026-06-04 · Implementation:** Routed Registry component term-window raw display-token extraction through shared greenfield label terms so fallback label and nearby-context windows no longer carry local regex token loops.
  - Scope: B-142
  - Evidence: src/odylith/runtime/domain_intelligence/greenfield_component_term_windows.py, src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py +1 more
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
- 2026-06-04: Routed confirmed Atlas proof-label word counts through `greenfield_confirmed_text.word_count`. `greenfield_confirmed_diagram_text.py` keeps proof-label cleanup, proof-review label selection, Mermaid label trimming, and short-label cleanup while confirmed text owns Markdown cleanup and visible word counting for semantic proof checkpoint and proof-review clause thresholds. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed semantic-model proof checkpoint word counts through `greenfield_confirmed_text.word_count`. `greenfield_semantic_model.py` keeps first-path contracts, ontology, component refs, workstream refs, diagram event graph assembly, and proof-obligation shaping while confirmed text owns Markdown cleanup and visible word counting for diagram-event proof checkpoint thresholds. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed component visible word-count thresholds through `greenfield_confirmed_text.word_count`. `greenfield_confirmed_components.py` keeps internal-system component generation, labels, kind selection, responsibility, boundary, dependency, interface, validation, and fallback contract shaping while confirmed text owns Markdown cleanup and visible word counting for responsibility-depth, generated-or-weak, and dependency-focus thresholds. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split specialized generated Registry component contract profiles into `greenfield_component_contract_profiles.py`. Document-context and status-view contract builders now own their profile-specific phrase extraction, transition selection, outside-boundary wording, and local proof rows while `greenfield_component_contract.py` stays below the 800-line soft limit as the profile selector and generic fallback contract owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split generated Registry component semantic context extraction into `greenfield_component_semantic_context.py`. Context-derived phrase extraction, late first-path/proof backfill selection, context anchor expansion, actor/action prefix removal, and context-backfill decisions now sit outside `greenfield_component_semantic_contract.py`, which stays below the 800-line soft limit as the semantic contract assembly owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split generated Registry component contract target parsing into `greenfield_component_contract_targets.py`. Rendered-spec issue parsing, duplicate repair-target dedupe, and operator-facing component-spec blocker copy now sit outside `greenfield_component_contract_differentiation.py`, which stays below the 800-line soft limit as the contract repair orchestrator. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-create apply-prewrite component and diagram rendering into `greenfield_apply_components.py` and `greenfield_apply_diagrams.py`. First-release Registry input shaping, dry-run component preview, in-memory Registry spec rendering, component dependency/risk/responsibility copy, Atlas source preview, and diagram ID allocation now sit outside `greenfield_apply_prewrite.py`, which stays below the 800-line soft limit as the staged package and remapping owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-create final governed writes into `greenfield_apply_write.py`. The owner now applies Radar source files, stale workstream cleanup, release targeting, program waves, Atlas scaffold/upsert writes, Registry component authoring, accepted-project memory, dashboard refresh, and next-step shaping while `greenfield_proposals.py` stays below the 800-line soft limit as the intent/proposal/prewrite transaction entrypoint. The same pass aligned blank component `release_scope` with the semantic builder and refreshed stale apply semantic models before completion gates run. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split first-path clause rendering into `greenfield_first_path_clauses.py` and shared first-path records into `greenfield_first_path_types.py`. `greenfield_first_path_semantics.py` now owns parsing and semantic model extraction only, while the clause owner renders action, capability, visible-result, action-chain, and trivial-start grammar for Radar, Registry, Atlas, runtime JSON, and dashboard copy. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed generated-artifact substance checks into `proposal_tribunal_substance.py`. The new owner handles confirmed Radar thinness, Registry component-contract substance, cross-axis proof leakage, Atlas scaffold-node rejection, first-path tail preservation, and first-boundary routing while `proposal_tribunal.py` stays focused on deterministic prewrite adjudication and topology/security/actor gates. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed-intent internal-system completion into `greenfield_confirmed_system_completion.py`. The owner now completes internal system rows, fallback systems, system labels, state labels, and context-clause matching while `greenfield_confirmed_intent_completion.py` stays focused on orchestration, core fields, product posture, title repair, and first-path/proof wording. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split Atlas first-path event-step derivation into `greenfield_sequence_steps.py`. The step owner now handles semantic events, launcher-only filtering, first-path fallback parsing, compound-step expansion, and dedupe while `greenfield_sequence_diagram.py` stays below the 800-line soft limit as the participant/component routing and Mermaid rendering owner. The pass also preserves final `act later` decision tails and short role-qualified component artifacts such as `person follow list` in confirmed create output. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed Atlas sequence-step display word counts through `greenfield_domain_term_index.label_terms`. `greenfield_sequence_steps.py` keeps event extraction, fallback splitting, launcher filtering, compound expansion, and dedupe while the shared term index owns display-token counting for launcher-only and numbered first-path filtering. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed first-path parser display step-token thresholds through `greenfield_domain_term_index.label_terms`. `greenfield_first_path_semantics.py` keeps prefix stripping, action splitting, role-can normalization, subjectless action normalization, material action selection, visible outcome selection, recovery extraction, and `FirstPathModel` assembly while the shared term index owns display-token counting for new-action clause and valid-step thresholds. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split Domain Intelligence artifact enrichment so `artifact_graph.py` owns graph normalization and `artifact_tribunal_actors.py` owns visible Tribunal actor projection. `artifact_enrichment.py` now stays below the 800-line soft limit as the artifact projection owner, and project-intelligence callers import graph and actor helpers from their dedicated owners. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed project-brief rendering into `greenfield_confirmed_project_brief.py` and consolidated greenfield command quoting into `greenfield_command_text.py`. `greenfield_confirmed_components.py` now stays below the 800-line soft limit as the confirmed Registry component generator instead of also owning project-readiness copy and host handoff commands. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Consolidated component-contract phrase and term helper ownership in `greenfield_component_terms.py`. Base contracts, semantic contracts, and contract differentiation now reuse `natural_phrase`, `phrase`, and `domain_terms` instead of carrying local `_term_phrase`, `_phrase`, or `_content_terms` clones, while all touched component-contract files stay below the 800-line soft limit. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split confirmed component completion into `greenfield_confirmed_component_completion.py`. Component contract normalization, contract-derived responsibility/boundary/interface/dependency/validation/risk repair, component risk enrichment, and component sentence repair now sit outside `greenfield_confirmed_completion.py`, which stays below the 800-line soft limit as the confirmed-create repair orchestrator. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Consolidated generated list-row coercion in `greenfield_rows.py`. Confirmed prewrite gating, the deterministic Tribunal, confirmed title repair, apply-prewrite remapping, confirmed completion, and post-confirm semantic/package checks now import `mapping_rows` or `dict_rows` from the shared owner instead of carrying private `_mapping_rows`/`_dict_rows` clones or a post-confirm-specific wrapper. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Extended shared row coercion to remaining component, backlog, handoff, created-row, proposal-row, and wave-row readers, and hardened semantic context cleanup for confirmed Registry contract text. `greenfield_backlog_impact.py`, `greenfield_experience.py`, `greenfield_confirmed_component_completion.py`, and `greenfield_component_contract_differentiation.py` now reuse `mapping_rows` or `dict_rows`, while `greenfield_component_semantic_context.py` strips metadata-led actor/action phrases and `greenfield_confirmed_project_brief.py` rewrites awkward show-actor-artifact copy before project posture text is rendered. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Consolidated confirmed-intent list text coercion in `greenfield_confirmed_text.py`. The parser, completion, actor-completion, system-completion, and validation owners now call `confirmed_text_values` instead of carrying local `_strings` helpers, so Markdown cleanup and strict accepted-intent list semantics stay in one shared confirmed-text owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed project-brief and project-intelligence word counting through `greenfield_confirmed_text.word_count`. The project-surface validators now keep schema and row-depth thresholds while confirmed text owns Markdown cleanup and visible word counting instead of local `_word_count` helpers. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed-intent parser word counting through `greenfield_confirmed_text.word_count`. The parser now keeps section inference, preamble paragraph selection, and accepted-field derivation while confirmed text owns Markdown cleanup and visible word counting instead of a parser-local `_word_count` helper. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Removed the remaining private coercion helpers from workstream Domain Intelligence and project-intelligence binding. `greenfield_workstream_intelligence.py` now uses `greenfield_text.text_values` directly instead of `_list_values`, and `project_intelligence_binding.py` uses `runtime.common.value_coercion.mapping_copy` instead of a local `_mapping` helper. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Split proposal project-brief rendering into `greenfield_project_brief.py`. Proposal text now imports `render_project_brief_lines`, while blueprint-section, customization-option, checkpoint, host-path, and generated-row rendering stay with the project-brief owner and reuse `greenfield_rows.mapping_rows`. `proposal_rendering.py` remains a general proposal text renderer below the 800-line soft limit. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-03: Routed component-axis term extraction through `greenfield_component_terms.py`. `greenfield_component_axes.py` now calls `domain_terms` and `term_phrase` for derived semantic axes and no longer owns local `_content_terms`, `_term_token`, `_phrase`, or `_normalize_axis_text` helpers, keeping Registry axis keys and generated component contracts on the same term owner. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed component contract field support-artifact phrase rendering through `greenfield_component_terms.py`. `greenfield_component_contract_fields.py` now calls the shared comma-clause `phrase` helper and no longer owns a local `_phrase` clone, keeping field-level accepted-input and produced-output wording on the same component-term owner as contracts, differentiation, and axes. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Split ordered component-local term indexing into `greenfield_component_term_index.py`. Component contracts, contract differentiation, component terms, and component quality gates now import `ordered_domain_terms` from the term-index owner, while `greenfield_component_contract_quality.py` no longer owns reusable ordered term extraction or a local `_term_token` cache. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Split reusable greenfield domain-term indexing into `greenfield_domain_term_index.py`. Product-risk genericity checks now call `ordered_terms` with risk-specific stopwords, and `greenfield_component_term_index.py` delegates to the same shared kernel while retaining component-specific stopwords, keeping Radar risk specificity and Registry component term matching on one normalization path. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Moved Registry spec term distinctiveness into `greenfield_component_term_index.py`. The term-index owner now exposes `component_domain_terms`, `section_domain_terms`, and `component_local_terms`, while `greenfield_component_contract_quality.py` keeps only quality failure decisions and no longer owns `domain_terms`, `_section_terms`, or `_local_domain_terms`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Moved confirmed-intent semantic term extraction into `greenfield_confirmed_text.semantic_terms`. Confirmed-intent validation now passes `CONFIRMED_INTENT_VALIDATION_STOPWORDS` into the text owner, internal-system row parsing imports the same owner, and the confirmed-intent tests were split so the main confirmed-intent suite stays below the test ceiling. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed Atlas sequence and first-path flowchart component matching through `greenfield_domain_term_index.ordered_terms`. The shared term index now supports `stem_ing=True` for callers that need gerund collapse, and `greenfield_sequence_diagram.py` no longer owns `_domain_terms` or direct token normalization. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed generated semantic model term extraction through `greenfield_domain_term_index.ordered_terms`. `greenfield_semantic_model.py` now passes semantic-model stopwords to the shared owner for ontology terms, required fields, event targets, and actor terms instead of owning `_semantic_terms` or direct token normalization. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed post-confirm semantic drift, repetition, and overlap term signatures through `greenfield_domain_term_index.ordered_terms`. `greenfield_post_confirm_semantic_drift.py` now keeps only post-confirm stopwords and separator cleanup instead of owning direct `normalize_domain_token` calls or local regex token loops. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed post-confirm repeated generated-term counting through `greenfield_domain_term_index.term_frequencies` and generated sentence length filtering through `greenfield_text.word_count`. `greenfield_post_confirm_semantic_drift.py` keeps stopwords, separator cleanup, repetition clustering, and drift thresholds while shared token owners handle reusable counts with one normalized pass. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed-artifact Tribunal substance terms through `greenfield_domain_term_index.ordered_terms`. `proposal_tribunal_substance.py` now keeps only Tribunal stopwords and Atlas action aliases instead of owning direct `normalize_domain_token` calls or local regex token loops for generated Radar, Registry, and Atlas substance checks. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed-artifact Tribunal accepted public-text product phrase matching through `greenfield_domain_term_index.label_terms`. `proposal_tribunal_substance.py` keeps scaffold repetition policy while the shared term index owns raw accepted-text tokenization for product phrases such as `evidence record`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed semantic-quality release-scope and scope-context term signatures through `greenfield_domain_term_index.ordered_terms`. The shared term index now accepts caller-owned exact aliases and prefix aliases, while `greenfield_semantic_quality.py` keeps only release-scope stopwords, alias policy, and release-scope decisions instead of direct token normalization. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed semantic-quality raw sentence-overlap and scoped-clause token extraction through `greenfield_domain_term_index.label_terms`. `greenfield_semantic_quality.py` now keeps overlap thresholds, release-scope decisions, and stopword policy while the shared term-index owner handles both normalized semantic terms and raw visible-token extraction. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed accepted-intent semantic term indexing through `greenfield_domain_term_index.ordered_terms` while keeping `greenfield_confirmed_text.semantic_terms` as the confirmed-intent API. The shared term index now accepts caller-owned `stem_ing_minimum_length`, and `greenfield_confirmed_text.py` keeps confirmed Markdown cleanup, stopword defaults, and caller handoff instead of direct token normalization. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed Registry component phrase identity terms and contract-field transition candidates through `greenfield_domain_term_index.ordered_terms`. `greenfield_component_terms.py` keeps artifact-carrier stopword policy, `greenfield_component_contract_fields.py` keeps transition-state decisions, and `greenfield_component_semantic_contract.py` imports the phrase-identity owner directly instead of wrapping it locally. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed base component contract profile token extraction through `greenfield_domain_term_index.ordered_terms`. `greenfield_component_contract.py` keeps profile selection, generic fallback contract assembly, focus phrase derivation, state terms, boundary clauses, and public contract field projection while the shared domain-term index owns reusable token parsing, short-term preservation, and plural folding for profile matching. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed-completion label focus and keyword extraction through `greenfield_domain_term_index.label_terms` and `ordered_terms`. `greenfield_confirmed_completion_text_model.py` keeps completion phrasing, generated labels, first-path/proof/state summaries, actor summaries, and backlog-to-component matching policy while the shared domain-term index owns visible label tokenization, plural folding, digit filtering, and reusable keyword parsing. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed public quality-gate prompt and semantic-contract term extraction through `greenfield_domain_term_index.ordered_terms`. The shared term index now accepts caller-owned `preserve_terms`, so `greenfield_quality_gate.py` can preserve short domain abbreviations while keeping prompt echo and public artifact quality checks off local regex token loops. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed first-path actor signature term extraction through `greenfield_domain_term_index.ordered_terms`. `greenfield_first_path_clauses.py` keeps first-path action, capability, visible-result, and actor-filtering grammar, while actor signatures share the generated-artifact term index with caller-owned stopwords and short actor-term preservation for labels such as AI, ML, UI, and UX. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed first-path actor-prefix display-token thresholds through `greenfield_domain_term_index.label_terms`. `greenfield_first_path_clauses.py` keeps first-path action, capability, visible-result, actor filtering, and actor-specific term policy while the shared term index counts display tokens for `strip_action_subject`, `_actor_signature`, and `leading_subject_prefix` prefix-length decisions. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed component domain-label token extraction through `greenfield_domain_term_index.label_terms`. The shared domain-term owner now has a visible-label path that preserves casing, acronyms, and alphanumeric terms while `greenfield_confirmed_components.py` keeps component naming policy and title casing without a local regex token loop. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed component kind-token extraction through `greenfield_text.visible_words`. `greenfield_confirmed_components.py` keeps client/adapter/service kind policy while shared greenfield text owns reusable visible-word splitting for hyphenated and slash-separated internal system names. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed component handoff workstream-title matching through `greenfield_domain_term_index.ordered_terms`. `greenfield_experience.py` keeps handoff thresholds and stopwords, while reusable title and component-label normalization shares the generated-artifact term index instead of a local `_meaningful_terms` regex helper. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed generated traceability semantic token extraction through `greenfield_domain_term_index.ordered_terms`. `greenfield_traceability.py` keeps component-workstream and diagram-link scoring plus compound identifier expansion, while plural and stopword normalization shares the generated-artifact term index instead of a local `_semantic_tokens` regex loop. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed Radar backlog text product-term matching through `greenfield_domain_term_index.ordered_terms`. `greenfield_confirmed_backlog_text_model.py` keeps backlog-specific stopwords and first-slice wording decisions, while `semantic_words` and `shares_product_terms` share plural and stopword normalization with the generated-artifact term index instead of local lower-case regex token loops. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed Radar backlog proof-focus word counts and repeated-required detection through `greenfield_confirmed_text.word_count` and `word_occurrences`. `greenfield_confirmed_backlog_text_model.py` keeps proof-focus selection, first-slice wording, mechanical-summary rejection, and product-term matching policy while confirmed text owns Markdown cleanup, visible word counting, and exact word occurrence counting. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Split Registry fallback component term-window parsing into `greenfield_component_term_windows.py`. `greenfield_component_contract_differentiation.py` keeps fallback-axis scoring and repair decisions, while the term-window owner handles component label compounds, nearby context windows, plural folding, and short label compounds without growing the near-limit `greenfield_component_terms.py` module. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Moved Registry literal component label-term extraction into `greenfield_component_term_windows.py`. Base component contracts, semantic component contracts, and fallback contract differentiation now share one label-term owner that preserves short labels and plural artifact-carrier phrases such as `policy guardrails` while still folding ordinary semantic plurals such as `status windows`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Moved generated Registry actor-role token detection into `greenfield_actor_terms.py` and cached action-form classification in `greenfield_component_terms.py`. Component artifact cleanup and semantic context extraction now share the same role classifier, so actor/action leads such as `inspector reviews permit note` are reduced to the owned artifact phrase `permit note` instead of leaking actor prose into Registry contracts. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Moved generated Registry generic actor-label prefix detection and localization into `greenfield_actor_terms.py`. Component contract fields, contract differentiation, and rendered contract quality now share one owner for operator/reviewer/owner/user prefixes, so artifact-bearing labels such as `Primary user request status` and `Risk reviewer guardrails` reduce to the owned artifact phrase while bare generic actor labels stay localized. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed proposal validation field-depth counts through `greenfield_text.word_count`. `proposal_validation.py` keeps proposal shape, evidence-tier, Mermaid, rationale, backlog, component, and diagram validation policy while shared text owns reusable word counting for arbitrary slash- and hyphen-bearing product phrases. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed program wave-to-workstream match terms through `greenfield_domain_term_index.ordered_terms`. `greenfield_programs.py` keeps release selector parsing, explicit workstream refs, fallback ordering, execution-wave document shape, and release-target helpers while the shared term index owns plural folding and reusable token filtering for arbitrary wave and backlog vocabulary. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed Registry contract field visible-word extraction through `greenfield_text.visible_words`. `greenfield_component_contract_fields.py` keeps shell-artifact rejection, status-only field policy, ranked-output normalization, and contract list cleanup while shared text owns reusable visible word splitting for hyphenated generated field phrases. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed Registry contract differentiation trigger matching through `greenfield_text.visible_words`. `greenfield_component_contract_differentiation.py` keeps fallback-axis scoring, sibling repair, and contract repair decisions while shared text owns reusable visible word splitting for hyphenated trigger phrases such as `status-window proof`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed Registry document-context and status-view profile object labels through `greenfield_domain_term_index.label_terms`. `greenfield_component_contract_profiles.py` keeps profile wording, proof rows, and state-object policy while the shared term index owns visible label tokenization for hyphenated and underscore-separated object labels. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed Registry semantic contract compact-artifact token counting through `greenfield_domain_term_index.label_terms`. `greenfield_component_semantic_contract.py` keeps object-phrase dedupe, compact-artifact preservation, phrase prioritization, and local contract assembly while the shared term index owns display-token parsing for hyphenated and underscore-separated artifact phrases. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed Registry term-window raw display-token extraction through `greenfield_domain_term_index.label_terms`. `greenfield_component_term_windows.py` keeps label-term preservation, compound construction, and nearby context-window policy while the shared term index owns reusable display-token parsing for component labels and context phrases. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed Registry artifact cleanup action-token checks through `greenfield_text.visible_words` and preserved slash-separated visible-result object phrases during cleanup. `greenfield_component_terms.py` keeps artifact phrase cleanup, actor/action trimming, action-form classification, artifact-carrier policy, and phrase identity while shared greenfield text owns reusable visible-word splitting for generated artifact phrases such as `web/ui surface`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed-intent title repair and system-label qualifier display tokens through `greenfield_domain_term_index.label_terms`. `greenfield_confirmed_intent_completion.py` keeps title repair, title noun selection, qualifier ranking, core-field completion, and product-posture completion while the shared term index owns reusable display-token extraction for accepted labels such as `AI/ML review record`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed canonical confirmed project-title repair acceptance checks through `greenfield_domain_term_index.label_terms`. `greenfield_confirmed_title_repair.py` keeps stale title detection, existing-title candidate selection, proposal-wide replacement, slug repair, and project-intelligence rebinding while the shared term index owns reusable display-token extraction for title candidates such as `AI/ML Review Workspace`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)
- 2026-06-04: Routed confirmed focus-label title token extraction through `greenfield_domain_term_index.label_terms`. `greenfield_confirmed_text.py` keeps confirmed Markdown cleanup, list coercion, semantic terms, word counts, repeated-word counts, title casing, focus-label selection, and domain object labels while the shared term index owns reusable display-token extraction for generated titles such as `Source-backed Review Workspace`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-202`)

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
- First-path parser display step-token thresholds must use
  `greenfield_domain_term_index.label_terms`.
  `greenfield_first_path_semantics.py` may own prefix stripping, action
  splitting, role-can normalization, subjectless action normalization,
  material action selection, visible outcome selection, recovery extraction,
  and `FirstPathModel` assembly, but it must not reintroduce local raw
  word-count regex loops for starts-new-action or valid-step filtering.
- Atlas first-path step derivation must stay in
  `greenfield_sequence_steps.py`. Sequence and flowchart renderers may call
  `sequence_event_steps`, but they must not re-own semantic event extraction,
  launcher-only filtering, fallback first-path splitting, compound-step
  expansion, or step dedupe. First-path scope detection must not classify
  user-decision tails such as `act later` as deferred release scope. Display
  word counts for launcher-only and numbered first-path filtering must use
  `greenfield_domain_term_index.label_terms`; the sequence step owner must not
  reintroduce local raw word-count regex loops.
- Generated Registry component artifact cleanup must preserve short
  role-qualified artifact identities when they end in an owned artifact noun,
  for example `person follow list` and `reviewer notes`; it may still strip
  generic actor noise from longer non-artifact prose.
- Component-contract phrase and term helpers must stay in
  `greenfield_component_terms.py`. Base component contracts, semantic
  contracts, and contract differentiation may call `natural_phrase`, `phrase`,
  and `domain_terms`, but they must not reintroduce local `_term_phrase`,
  `_phrase`, or `_content_terms` clones for generated Registry contract text.
- Registry fallback component label compounds and nearby context-window terms
  must stay in `greenfield_component_term_windows.py`.
  `greenfield_component_contract_differentiation.py` may own fallback-axis
  scoring, sibling context, and repair decisions, but it must not reintroduce
  `_literal_label_compounds`, `_nearby_content_terms`, or local regex token
  loops for fallback component label/context matching. The near-limit
  `greenfield_component_terms.py` module must not absorb that windowing owner
  just to hide the helper movement.
- Registry literal component label terms and label compounds must stay in
  `greenfield_component_term_windows.py`. `greenfield_component_contract.py`,
  `greenfield_component_contract_fields.py`, and
  `greenfield_component_semantic_contract.py` may own contract field wording,
  artifact ranking, and semantic assembly, but they must not reintroduce local
  literal-label regex helpers, pass-through wrappers, or caller-local label
  compound extraction. The shared owner must preserve short visible labels and
  plural artifact-carrier nouns such as `policy guardrails` while still folding
  ordinary semantic plurals such as `status windows`.
- Registry component term-window raw display-token extraction must use
  `greenfield_domain_term_index.label_terms`.
  `greenfield_component_term_windows.py` may own label-term preservation,
  compound construction, and nearby context-window policy, but it must not
  reintroduce local `re.findall` token loops for `_domain_token_stream` or
  `_preserved_label_terms`.
- Generated Registry actor-role token detection must stay in
  `greenfield_actor_terms.py`, and action-form classification used by component
  artifact cleanup must stay cached in `greenfield_component_terms.py`.
  Component artifact cleanup and semantic context extraction may own phrase
  ranking and context carry policy, but they must not reintroduce local
  actor-role lists, suffix-only actor checks, or non-cached action-form token
  loops that let actor/action leads such as `inspector reviews` leak into owned
  artifact nouns.
- Generated Registry generic actor-label prefix detection and localization must
  stay in `greenfield_actor_terms.py`. Component contract fields, contract
  differentiation, and component contract quality may call
  `generic_actor_label_prefix`, `starts_with_generic_actor_label`, and
  `localize_generic_actor_label`, but they must not reintroduce local
  operator/reviewer/owner/user prefix regexes for generated contract fields.
- Component contract field wording must also use
  `greenfield_component_terms.phrase` for comma-clause support-artifact text.
  `greenfield_component_contract_fields.py` may call the shared helper, but it
  must not reintroduce a local `_phrase` clone for accepted-input,
  produced-output, or adjustment-support wording.
- Registry fallback-axis trigger matching must use
  `greenfield_text.visible_words`. `greenfield_component_contract_differentiation.py`
  may own local-score thresholds, trigger-hit weighting, sibling repair, and
  repair decisions, but it must not reintroduce local word-token `re.findall`
  loops for `_trigger_hits`.
- Registry artifact cleanup action-token checks must use
  `greenfield_text.visible_words`. `greenfield_component_terms.py` may own
  artifact phrase cleanup, actor/action trimming, action-form classification,
  artifact-carrier policy, and phrase identity, but it must not reintroduce
  local word-token `re.findall(r"[a-z0-9]+", lowered)` loops for cleanup
  filtering or malformed slash-separated visible-result objects such as
  `web state/ui surface`.
- Registry document-context and status-view profile object phrases must use
  `greenfield_domain_term_index.label_terms` with profile-owned stopwords.
  `greenfield_component_contract_profiles.py` may own profile wording, local
  proof rows, and state-object policy, but it must not reintroduce local display
  token regex loops for `_object_phrase`.
- Registry semantic contract compact-artifact phrase checks must use
  `greenfield_domain_term_index.label_terms`.
  `greenfield_component_semantic_contract.py` may own object-phrase dedupe,
  compact-artifact preservation, phrase prioritization, and local contract
  assembly, but it must not reintroduce local display-token regex loops for
  `_compact_artifact_phrase`.
- Ordered component-local term indexing must stay in
  `greenfield_component_term_index.py`. Component contracts, component terms,
  contract differentiation, and quality gates may call `ordered_domain_terms`,
  but `greenfield_component_contract_quality.py` must not reintroduce local
  `ordered_domain_terms` or `_term_token` helpers.
- Reusable greenfield term normalization must stay in
  `greenfield_domain_term_index.py`. Radar product-risk specificity,
  component-local term indexing, and future artifact-specific overlap checks
  may pass surface-owned stopwords, exact aliases, prefix aliases, or
  caller-owned gerund thresholds or short-term preservation to
  `ordered_terms`, but they must not reintroduce private `_domain_terms`,
  `_term_token`, or regex token loops for generated-artifact specificity.
- Component handoff workstream-title matching must use
  `greenfield_domain_term_index.ordered_terms` with caller-owned handoff
  stopwords. `greenfield_experience.py` may own match thresholds and first-slice
  fallback policy, but it must not reintroduce `_meaningful_terms` or local
  `re.findall` token loops for Radar-to-Registry handoff matching.
- Generated traceability semantic token extraction must use
  `greenfield_domain_term_index.ordered_terms` with caller-owned traceability
  stopwords and `minimum=3`. `greenfield_traceability.py` may own overlap
  scoring, fallback parent assignment, and compound identifier expansion, but it
  must not reintroduce local `re.findall` token loops for generated
  Radar-to-Registry-to-Atlas traceability matching.
- Confirmed Radar backlog semantic term extraction and product-term sharing must
  use `greenfield_domain_term_index.ordered_terms` with caller-owned backlog
  stopwords. `greenfield_confirmed_backlog_text_model.py` may own first-slice
  wording policy and generic product-share stopwords, but it must not reintroduce
  local lower-case `re.findall` token loops for `semantic_words` or
  `shares_product_terms`.
- Visible generated-label token extraction must stay in
  `greenfield_domain_term_index.label_terms` when callers need display words
  rather than semantic singularization. `greenfield_confirmed_components.py`
  may own component-label stopwords and title casing, but it must not
  reintroduce a local `for raw in re.findall` token loop for `domain_label`.
- Confirmed-intent title repair and system-label qualifier display tokens must
  use `greenfield_domain_term_index.label_terms`.
  `greenfield_confirmed_intent_completion.py` may own title repair, title noun
  selection, qualifier ranking, core-field completion, and product-posture
  completion, but it must not reintroduce local `re.findall(r"[A-Za-z0-9]+",
  ...)` token loops that can clip slash-separated accepted labels such as
  `AI/ML review record`.
- Canonical confirmed project-title repair acceptance checks must use
  `greenfield_domain_term_index.label_terms`.
  `greenfield_confirmed_title_repair.py` may own stale title detection,
  existing-title candidate selection, proposal-wide replacement, slug repair,
  and project-intelligence rebinding, but it must not reintroduce local
  `re.findall(r"[A-Za-z0-9]+", ...)` token loops for title or candidate
  acceptance.
- Confirmed focus-label title token extraction must use
  `greenfield_domain_term_index.label_terms`.
  `greenfield_confirmed_text.py` may own confirmed-text cleanup, title casing,
  focus-label selection, and domain object labels, but it must not reintroduce
  local `re.findall(r"[A-Za-z0-9]+", title)` loops for focus-label selection.
- Public quality-gate prompt and semantic-contract term extraction must use
  `greenfield_domain_term_index.ordered_terms`. `greenfield_quality_gate.py`
  may own public-quality stopwords, failure messages, and short domain
  abbreviation choices, but it must pass those choices through
  `preserve_terms` and must not import `normalize_domain_token`, define
  `_singular` token wrappers, or loop over regex tokens locally for prompt echo
  or semantic-contract noun checks.
- First-path actor signature extraction must use
  `greenfield_domain_term_index.ordered_terms`. `greenfield_first_path_clauses.py`
  may own action, capability, visible-result, and actor-filtering grammar, plus
  actor-specific stopwords and short actor-term preservation, but it must not
  import `normalize_domain_token` or reintroduce a local regex token loop for
  actor signatures.
- First-path actor-prefix display-token thresholds must use
  `greenfield_domain_term_index.label_terms`.
  `greenfield_first_path_clauses.py` may own action, capability,
  visible-result, actor filtering, and actor-specific term policy, but it must
  not reintroduce local raw word-count regex loops for `strip_action_subject`,
  `_actor_signature`, or `leading_subject_prefix` prefix-length decisions.
- Registry component phrase identity and contract-field transition candidate
  extraction must use `greenfield_domain_term_index.ordered_terms` for reusable
  token indexing. `greenfield_component_terms.py` may retain artifact-carrier
  stopword policy, `greenfield_component_contract_fields.py` may retain
  state/transition decisions, and `greenfield_component_semantic_contract.py`
  may import `phrase_identity_terms` directly, but these paths must not import
  `normalize_domain_token`, reintroduce local `for raw in re.findall` token
  loops, or wrap phrase identity behind a pass-through helper.
- Base component contract profile selection must use
  `greenfield_domain_term_index.ordered_terms(..., minimum=1)` for focused
  component label/kind matching. `greenfield_component_contract.py` may own
  profile vocabulary, profile decisions, generic fallback contract assembly,
  focus phrase derivation, state terms, boundary clauses, and public contract
  field projection, but it must not reintroduce `_word_set` or local raw token
  regex loops for profile matching.
- Atlas sequence and first-path flowchart routing must use
  `greenfield_domain_term_index.ordered_terms` for component and actor text
  matching. Sequence-specific stopwords and `stem_ing=True` may remain
  caller-owned, but the sequence renderer must not reintroduce `_domain_terms`,
  `_term_token`, or direct `normalize_domain_token` loops.
- Generated semantic model term extraction must use
  `greenfield_domain_term_index.ordered_terms` for ontology terms, required
  fields, event targets, and actor terms. Semantic-model stopwords may remain
  caller-owned, but `greenfield_semantic_model.py` must not reintroduce
  `_semantic_terms`, `_term_token`, or direct `normalize_domain_token` loops.
- Post-confirm semantic drift, repetition, and overlap signatures must use
  `greenfield_domain_term_index.ordered_terms`. The drift checker may retain
  post-confirm stopwords and separator cleanup, but it must not reintroduce
  `_term_token`, local regex token loops, or direct `normalize_domain_token`
  calls.
- Post-confirm repeated generated-term counts must use
  `greenfield_domain_term_index.term_frequencies`, and generated sentence
  length filtering must use `greenfield_text.word_count`. The drift checker may
  retain stopwords, separator cleanup, repetition clustering, and thresholds,
  but it must not reintroduce local `len(re.findall(...))` count gates or
  per-term regex scans.
- Confirmed artifact Tribunal substance signatures must use
  `greenfield_domain_term_index.ordered_terms` for generated Radar substance,
  Registry proof-boundary, and Atlas first-path tail checks. The Tribunal owner
  may retain Tribunal stopwords and Atlas action aliases, but it must not
  reintroduce `_term_set` token loops, direct `normalize_domain_token` calls, or
  regex token loops for reusable generated-artifact vocabulary.
- Semantic-quality release-scope and scope-context term signatures must use
  `greenfield_domain_term_index.ordered_terms`. Semantic quality may retain
  release-scope stopwords and caller-owned alias policy, but it must not
  reintroduce `_terms` token loops or direct `normalize_domain_token` calls.
- Semantic-quality raw sentence-overlap and scoped-clause token extraction must
  use `greenfield_domain_term_index.label_terms`. Semantic quality may retain
  n-gram size, overlap thresholds, scope markers, and stopword policy, but it
  must not reintroduce local `re.findall` token loops for raw overlap or
  scope-context word counting.
- Registry spec term-set and distinctiveness scoring must stay in
  `greenfield_component_term_index.py`. Component quality gates may call
  `component_domain_terms`, `section_domain_terms`, and `component_local_terms`
  to decide generated-spec failures, but they must not define `domain_terms`,
  `_section_terms`, `_local_domain_terms`, or direct stopword ownership for
  Registry spec distinctiveness.
- Confirmed-intent semantic term extraction must stay in
  `greenfield_confirmed_text.py`. Validation, parser, actor, and
  internal-system modules may call `semantic_terms` with caller-owned stopwords,
  but reusable token indexing must go through
  `greenfield_domain_term_index.ordered_terms`. Confirmed-text callers must not
  reintroduce `_TERM_STOPWORDS`, `_semantic_terms`, direct
  `normalize_domain_token` imports, or local regex token loops for accepted
  Product Intent semantic overlap.
- Confirmed-completion label focus and keyword extraction must use
  `greenfield_domain_term_index.label_terms` and `ordered_terms`.
  `greenfield_confirmed_completion_text_model.py` may own completion phrasing,
  generated labels, summaries, actor text, and backlog-to-component matching
  policy, but it must not reintroduce local label regex loops or private
  character-filtering keyword loops for completion matching.
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
- Confirmed project-surface visible word counting must stay in
  `greenfield_confirmed_text.word_count`. `greenfield_project_brief.py` and
  `greenfield_project_intelligence.py` may own schema shape, minimum-row
  thresholds, and issue text, but they must not reintroduce local `_word_count`
  helpers for project brief or project intelligence shallow-row checks.
- Confirmed Radar backlog proof-focus word-count thresholds and repeated-word
  checks must stay in `greenfield_confirmed_text.word_count` and
  `word_occurrences`. `greenfield_confirmed_backlog_text_model.py` may own
  proof-focus selection, first-slice wording, rationale-line policy, and
  mechanical-summary rejection, but it must not reintroduce local raw regex
  count gates for proof-focus length or repeated `required` detection.
- Confirmed Atlas proof-label visible word counting must stay in
  `greenfield_confirmed_text.word_count`.
  `greenfield_confirmed_diagram_text.py` may own semantic proof checkpoint
  cleanup, proof-review label selection, Mermaid label trimming, and short-label
  cleanup, but it must not reintroduce local raw word-count regex loops for
  confirmed Atlas proof-label thresholds.
- Semantic-model proof checkpoint visible word counting must stay in
  `greenfield_confirmed_text.word_count`. `greenfield_semantic_model.py` may own
  first-path contracts, ontology, component refs, workstream refs, diagram event
  graph assembly, and proof-obligation shaping, but it must not reintroduce
  local raw word-count regex loops for diagram-event proof checkpoint thresholds.
- Confirmed component visible word-count thresholds must stay in
  `greenfield_confirmed_text.word_count`.
  `greenfield_confirmed_components.py` may own internal-system component
  generation, labels, kind selection, responsibility, boundary, dependency,
  interface, validation, and fallback contract shaping, but it must not
  reintroduce local raw word-count regex loops for responsibility-depth,
  generated-or-weak, or dependency-focus thresholds.
- Confirmed component kind-token extraction must use
  `greenfield_text.visible_words`. `greenfield_confirmed_components.py` may own
  client, adapter, and service kind policy, but it must not reintroduce local
  `re.findall(r"[a-z0-9]+", ...)` loops for `_contains_kind_token`.
- Confirmed-intent parser visible word counting must stay in
  `greenfield_confirmed_text.word_count`. `greenfield_confirmed_intent.py` may
  own Markdown/JSON section parsing, preamble paragraph selection, and accepted
  field derivation, but it must not reintroduce a local `def _word_count`.
- General workstream Domain Intelligence text-list coercion must use
  `greenfield_text.text_values` directly; `greenfield_workstream_intelligence.py`
  must not reintroduce `_list_values`. Project-intelligence artifact binding
  must use `runtime.common.value_coercion.mapping_copy` for mapping coercion
  instead of a local `_mapping` helper.
- Proposal project-brief rendering must stay in
  `greenfield_project_brief.py`. `proposal_rendering.py` may call
  `render_project_brief_lines`, but it must not reintroduce
  `_project_brief_lines`, blueprint-section, customization-option, checkpoint,
  or host-path rendering helpers. Project-brief row rendering must use shared
  generated-row coercion from `greenfield_rows.py`.
- Derived component-axis term extraction must use
  `greenfield_component_terms.domain_terms`, and component-axis local wording
  must use `greenfield_component_terms.term_phrase`. `greenfield_component_axes.py`
  must not reintroduce local `_content_terms`, `_term_token`, `_phrase`, or
  `_normalize_axis_text` helpers.
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
- Proposal validation field-depth checks for backlog metrics, rationale lines,
  component responsibilities, diagram component descriptions, and required
  proposal fields must use `greenfield_text.word_count`. `proposal_validation.py`
  may own minimum thresholds and issue copy, but it must not reintroduce
  `_meaningful_word_count` or local raw word-count regexes.
- Program wave-to-workstream matching must use
  `greenfield_domain_term_index.ordered_terms` with program-owned stopwords and
  a three-character minimum. `greenfield_programs.py` may own explicit ref
  resolution, wave fallback order, release selector helpers, and execution-wave
  document shape, but it must not reintroduce local `re.findall` token loops for
  wave/backlog matching.
- Registry contract field visible-word extraction for status-only fragments and
  ranked contract phrases must use `greenfield_text.visible_words`.
  `greenfield_component_contract_fields.py` may own shell-artifact rejection,
  status-only policy, ranked-output normalization, and contract list cleanup,
  but it must not reintroduce local word-token `re.findall` loops for those
  field checks.
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
  Normalized generated-artifact terms must use
  `greenfield_domain_term_index.ordered_terms`, and accepted public-text
  product phrase exceptions must use `greenfield_domain_term_index.label_terms`;
  the Tribunal substance gate must not reintroduce local accepted-term regex
  loops.
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
- `tests/unit/runtime/test_greenfield_coercion_hygiene.py`
- `tests/unit/runtime/test_greenfield_project_brief_rendering.py`
- `tests/unit/runtime/test_greenfield_component_spec_quality.py`
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
