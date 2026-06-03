status: implementation

idea_id: B-142

title: Universal greenfield domain intelligence

date: 2026-05-03

priority: P1

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: consumer lane,domain-intelligence,analysis-engine,radar,registry,atlas,compass,intervention-engine,host-adapters

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Operator-facing greenfield UX failure blocked a core consumer-lane onboarding path and belongs in the v0.1.14 release target alongside cross-host latency, intervention integrity, Casebook migration discipline, and Atlas topology quality.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-05/2026-05-01-cross-host-hook-latency-and-migration-hardening.md

execution_model: standard

workstream_type: standalone

workstream_parent: 

workstream_children: 

workstream_depends_on: B-141

workstream_blocks: 

related_diagram_ids: D-043

workstream_reopens: 

workstream_reopened_by: 

workstream_split_from: 

workstream_split_into: 

workstream_merged_into: 

workstream_merged_from: 

supersedes: 

superseded_by: 

## Problem
Empty or thin consumer repos could dead-end on broad project intent such as building an ecommerce site because Odylith treated missing app source as a hard refusal point instead of producing a confirmation-gated governance proposal. That made the consumer lane accurate but unhelpful, and it left Radar, Registry, Atlas, program waves, release planning, and validation strategy uncaptured until the operator supplied fully-formed governance fields.

## Customer
Consumer-lane operators starting a new product, research project, science or math codebase, data platform, cloud platform, security workflow, device workflow, CLI, library, app, game, or education experience before source-backed boundaries exist.

## Opportunity
Add an Odylith-owned confirmed greenfield path that turns vague or precise project intent into concrete backlog, program waves, provisional release plan, planned Registry components, Atlas topology, assumptions, risks, and validation obligations while keeping observed source, user intent, and Odylith assumptions distinct.

## Proposed Solution
Create a first-class `runtime/domain_intelligence` package that makes Odylith own the evidence/schema/proposal/apply layer end to end after Product Intent Confirmation. `odylith greenfield propose` stays a no-write Product Intent Confirmation path so the host can narrate product story, actors, systems, assumptions, ambiguities, and next choices in normal chat. After confirmation, `odylith greenfield create --confirm` builds an apply-ready proposal inside Odylith, validates the same product shape, runs a deterministic greenfield Tribunal, rejects disconnected or duplicated topology, writes only through owned Radar, Registry, Atlas, release-targeting, and Compass memory paths, and performs one final Radar/Registry/Atlas/Compass refresh after all accepted artifacts exist. `propose --confirm-intent --format json` remains an optional review/export artifact, not the default host-authored write path.

## Research Signals
External ecosystem checks argue against a narrow canned project taxonomy. GitHub Octoverse 2025 shows high-volume new repository creation, AI/agent growth, TypeScript-heavy application work, Python/Jupyter AI and data-science work, and private/product repos growing alongside public open source. CNCF organizes cloud-native work around infrastructure, delivery, observability, security, AI/ML, and runtime ecosystems. Apache describes mature open-source projects across data, cloud, search, libraries, geospatial, IoT, and related categories. NASA's software and open-data surfaces show science projects built from code, data, analysis pipelines, simulation/modeling tools, visualization, reproducibility, and sustained scientific libraries. Those signals prove greenfield intent is open-world; the durable contract is therefore generic product-first narration plus Odylith-owned apply-ready proposal generation, validation, topology hygiene, release targeting, program/wave formation, and durable memory.

## Scope
- Add no-write `odylith greenfield propose` for Product Intent Confirmation.
- Make the no-write Product Intent Confirmation visibly sectioned in every
  host lane: title, Product story, State object, First complete path, Human
  actors, External systems, Internal product systems, Critical assumptions,
  Ambiguities, Proof boundary, and Confirm/Edit/Reject. Do not allow one large
  prose block, decorative Markdown around normal domain nouns, or hidden
  structure that only the host model can infer.
- Add confirmed `odylith greenfield create --confirm` for Odylith-owned apply-ready proposal generation and governed writes.
- Keep `odylith greenfield apply` as the lower-level validated proposal-file path, not the default host workflow.
- Keep host adapters thin; every supported host routes to the same CLI/runtime path.
- Let the host model reason over any product, science, math, research,
  infrastructure, art, education, policy, device, data, or mixed project shape;
  do not constrain the proposal to an in-code domain list.
- Require the confirmed proposal to carry concrete backlog candidates,
  candidate Registry components, Atlas Mermaid sources,
  program formation, wave-to-workstream policy, release strategy, validation
  obligations, risks, assumptions, and open questions.
- Default apply-ready greenfield scaffolds must carry a multi-view Atlas
  architecture suite, not a token diagram pair: at minimum topology,
  first-slice sequence, component ownership, state/data contract, and
  validation/release topology; domain-specific profiles should add the
  operational-risk views the prompt makes material.
- Preserve evidence separation: observed source, user intent, and Odylith assumptions must stay distinct.
- Keep Odylith CLI proposal generation provider-free by default; the active host
  model performs the reasoning already happening in the chat.
- Write only after explicit confirmation and reject missing or duplicated Atlas
  topology before any governed file changes.
- Filter Compass timeline audit entries so zero-file prompt-intervention narration does not become fake implementation history.

## Non-Goals
- Do not add a separate provider-backed enrichment service in v0.1.14.
- Do not let host-specific Claude or Codex hooks own the proposal logic.
- Do not turn greenfield assumptions into source-backed governance claims.

## Risks
- Broad prompts can sound authoritative even when source evidence is empty; every generated detail must carry user-intent or Odylith-assumption evidence.
- Host proposals can drift into generic narration if Odylith accepts missing or
  duplicated topology; apply-time validation must fail before writes.
- Generic science/math routing can produce harmful advice if proof projects,
  notebook/statistical analysis, numerical solvers, ML experiments, and
  geospatial workflows share one validation script.
- Apply-time writes can pollute consumer repos unless they stay confirmation-gated and route through owned Radar, Registry, Atlas, and release authoring paths.

## Dependencies
- Depends on B-141 for the v0.1.14 host/runtime integrity lane: greenfield prompt routing must preserve low-latency host behavior, Intervention Engine separation, consumer-lane feature integrity, robust upgrade migration, and generated-surface refresh proof.

## Success Metrics
Greenfield propose returns a low-latency, provider_calls=0 Product Intent Confirmation request for any vague or precise greenfield prompt.
Product Intent Confirmation guidance requires scannable sectioned Markdown, short paragraphs, bullets where appropriate, and plain domain terms with no code ticks or decorative bold markers.
Greenfield create confirmed by the operator builds an apply-ready proposal inside Odylith with backlog candidates, program waves, release plan, planned Registry components, draft Atlas Mermaid sources, assumptions, risks, validation strategy, open questions, and exact governed-write evidence.
Provider-free greenfield scaffolds include a multi-view Atlas suite with mutually traceable workstream/component links; complex physical, analytical, and operational domains can add risk, safety, telemetry, deployment-boundary, and observability/audit views without hard-coded domain families.
Greenfield proposals carry a project-first brief before backlog: direction options, pre-coding checkpoints, coding-readiness gates, and host-independent commands must be visible in text and JSON before apply.
Greenfield Registry component specs stay component-owned: they must not copy project-level risk/security/compliance posture into every dossier, and each spec must name the component's own boundary, outside-boundary exclusions, collaborators, interfaces, failure modes, proof obligations, first source path, most specific child workstream anchor, and component-local diagram set instead of project-wide topology links.
Greenfield create/apply writes through owned Radar, Registry, Atlas, release-targeting, and Compass memory paths only after --confirm, preserving user_intent evidence and source-backed truth separation.
Apply rejects missing Mermaid source, duplicated diagram source, incomplete proposal sections, and invalid evidence tiers before any governed write.
Apply/create closeout leads with the project workstream and readiness gates, then names the eventual first coding workstream as a later lane rather than the immediate next action.
Host prompt routing avoids noisy raw Observation chatter for normal greenfield intents while preserving earned intervention paths.
Greenfield create/apply runs a deterministic proposal Tribunal before any governed write and refreshes Radar, Registry, Atlas, and Compass once after all accepted artifacts are written.
Compass timeline audit filters zero-file prompt-intervention narration so routing notes do not render as fake implementation history.

## Current Completion Gate
- Confirmed greenfield creation must build one typed semantic model before rendering any governed surface: `FirstPathContract`, `DomainOntology`, `ComponentContract`, `ReleaseScope`, `WorkstreamContract`, `DiagramEventGraph`, and `ProofObligation`.
- Registry, Radar, Atlas, project intelligence, release topology, and proof review must render from that typed model instead of independently re-parsing loose prose.
- The quality gate must fail closed before writes on first-path drift, provisional-title leakage, wrong-domain vocabulary, malformed ownership grammar, dangling punctuation, clipped sentences, duplicated words, proof-token soup, repeated proof walls, deferred-scope leakage, and missing active-release topology.
- The proof suite must include adversarial greenfield fixtures across unrelated domains and must assert zero leakage between fixture term signatures.
- Completion requires an end-to-end `greenfield create --confirm` proof that produces premium, domain-specific Radar workstreams, Registry component contracts, Atlas diagrams, project story, release assignment, and Tribunal evidence without adding project-specific logic to Odylith product code.

## Validation
- Unit tests for the Product Intent request contract, open-world confirmed proposal generation, required Mermaid sources, duplicate-topology rejection, program waves, release plan, CLI JSON, host greenfield routing, component authoring user-intent metadata, and Compass zero-file intervention chatter filtering.
- CLI proof for `odylith greenfield propose --format json` on empty/thin repo posture.
- Governance proof through Casebook, Radar, Registry, Atlas, and Compass refreshes.
- Browser proof for refreshed Radar, Registry, Atlas, Casebook, and Compass surfaces after generated assets update.

## Validation Evidence
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_greenfield_host_routing.py tests/unit/runtime/test_component_authoring.py tests/unit/runtime/test_compass_transaction_runtime.py tests/unit/runtime/test_show_capabilities.py tests/unit/test_cli.py` passed with 200 tests.
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_agents.py tests/unit/install/test_codex_project_assets.py tests/unit/install/test_claude_effective_settings.py tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_casebook_source_validation.py tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_validate_guidance_behavior.py tests/unit/runtime/test_validate_discipline.py tests/unit/install/test_migration_runtime.py tests/unit/install/test_casebook_metadata_migration.py tests/integration/install/test_lifecycle_simulator.py tests/integration/runtime/test_governance_sync_performance.py` passed with 269 tests.
- Full browser proof passed with 185 tests and 1 skipped case across Atlas, Casebook, Compass, Radar, Registry, intervention visibility, filter audit, onboarding, and regression surfaces.
- Fresh consumer proof installed the shipped runtime, executed source v0.1.13
  `greenfield propose/apply`, and confirmed confirmation-gated greenfield
  writes into backlog, Registry, Atlas, Compass memory, and a bootstrapped
  `next` release selector after explicit confirmation.
- Governance proof refreshed Casebook, Radar, Registry, Atlas, and Compass; `casebook validate`, `backlog-contract`, `plan-workstream-binding`, `plan-risk-mitigation`, `release migration-gate --target-version 0.1.13`, and `git diff --check` passed.
- Engine-integrity follow-up proved the Domain Intelligence capability map,
  markup-safe repo identity extraction, host routing, and science/math
  greenfield proposal path through the 568-test engine suite, the 208-test
  host/migration suite, and the 185-test browser matrix without provider calls
  or consumer-lane source claims.
- 2026-05-08 greenfield Atlas suite hardening proved the provider-free generic
  scaffold now emits the baseline architecture views and richer accepted
  scenarios can emit additional domain-specific views while validation and Tribunal still
  pass: `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_greenfield_atlas_contract.py
  tests/unit/runtime/test_compass_dashboard_shell.py::test_workstream_and_registry_links_stay_cross_surface_and_without_footer_actions
  tests/integration/runtime/test_surface_browser_smoke.py::test_compass_current_workstreams_excludes_rows_already_represented_in_programs_or_release_targets
  tests/unit/test_cli.py::test_release_migration_gate_json_reports_registered_runtime
  tests/unit/test_cli.py::test_greenfield_propose_command_is_provider_free
  tests/unit/test_cli.py::test_greenfield_create_help_forwards_backend_flags
  tests/unit/test_cli.py::test_greenfield_apply_help_forwards_backend_flags`
  (`43 passed`); `odylith sync --repo-root . --check-only --impact-mode
  selective`; `odylith casebook validate`; `odylith release migration-gate
  --target-version 0.1.15 --json` (`blocked_manual_migrations=0`); `git diff
  --check`; `python -m py_compile` for the touched Domain Intelligence modules.
- 2026-05-08 project-first greenfield UX hardening proved proposal text, JSON,
  legacy normalization, validation rejection, customization option coverage,
  and apply/create closeout now prioritize project shaping before coding:
  `PYTHONPATH=src pytest -q tests/unit/runtime/test_greenfield_proposals.py`
  (`33 passed`). Casebook bug `CB-186` captures the fixed-pending-release UX
  regression.
- 2026-05-08 project-intelligence deepening added a canonical
  `project_intelligence` object before the project brief and backlog, covering
  intent, scope, ontology, state, operators, constraints, truth map, evidence,
  decisions, assumptions, topology, invariants, risks, validation, artifacts,
  owners, execution memory, metrics, change rules, conflict rules, and transfer
  priors. The CLI text now renders that control surface first, JSON carries the
  same object, apply persists it into the parent Radar workstream, and managed
  greenfield guidance tells Codex, Claude Code, and direct CLI users not to
  rush to `start B-***` before project acceptance and a child technical plan.
  Proof: `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_greenfield_proposals.py` (`34 passed`),
  `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_greenfield_atlas_contract.py
  tests/unit/runtime/test_greenfield_host_routing.py tests/unit/test_cli.py`
  (`225 passed`), live `odylith greenfield propose` text inspection, and
  `odylith release migration-gate --target-version 0.1.15 --json`
  (`blocked_manual_migrations=0`).
- 2026-05-08 explicit invalidation and ownership hardening made
  `invalidation_rules` a validated project-intelligence layer and made child
  Radar workstream Domain Intelligence validate first-class `scope`, `owners`,
  and `invalidation_rules` layers. The workstream term tables were split into
  `greenfield_workstream_terms.py` so the generator stays under the source-size
  soft limit instead of becoming a swollen payload builder. Proof:
  `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_greenfield_intelligence_schema.py
  tests/unit/runtime/test_greenfield_proposals.py` (`36 passed`),
  `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_greenfield_intelligence_schema.py
  tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_greenfield_atlas_contract.py
  tests/unit/runtime/test_greenfield_host_routing.py tests/unit/test_cli.py`
  (`227 passed`), and the bundle/hygiene mirror slice
  (`tests/unit/runtime/test_source_bundle_mirror.py
  tests/unit/install/test_codex_project_assets.py
  tests/unit/install/test_agents.py tests/unit/runtime/test_hygiene.py`,
  `101 passed`).
- 2026-05-08 component-spec bespoke hardening proved generated Registry specs
  no longer inherit project-wide risk/security/compliance narrative, render
  component-named boundaries/contracts/proof/failure/runway sections, extract
  outside-boundary exclusions, and anchor each component to its most specific
  child workstream (`Risk Signal Engine` -> `B-003`, `Scenario Replay Harness`
  -> `B-004`): `PYTHONPATH=src pytest -q
  tests/unit/runtime/test_greenfield_proposals.py` (`33 passed`). Casebook bug
  `CB-187` captures the fixed-pending-release UX regression.
- 2026-05-08 component-spec topology tightening moved broad project links back
  to Radar/Atlas and kept Registry dossiers component-local: external-domain generated
  specs now bind Risk Console to `B-002` and `D-002,D-003`, Risk Signal Engine
  to `B-003` and `D-002,D-003,D-004`, Scenario Replay Harness to `B-004` and
  `D-005`; host-authored components without component-level diagram refs no
  longer inherit system-context/program-wave diagrams. Proof:
  `.venv/bin/python -m pytest tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_component_authoring.py
  tests/unit/runtime/test_governed_artifact_tribunal.py -q` (`39 passed`).
- 2026-05-08 project-first UX deepening made proposal text render a fuller
  project intelligence board before backlog, including all control-surface
  rows, complete customization flow through the no-code-until-plan step, deeper
  per-layer project reality, project design board rows, host-independent
  "customize by saying" examples, and apply/create closeouts that label the
  child workstream as a future implementation lane after gates instead of an
  immediate coding instruction. Proof: `.venv/bin/python -m pytest
  tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_greenfield_intelligence_schema.py
  tests/unit/runtime/test_component_authoring.py
  tests/unit/install/test_local_release_smoke.py -q` (`58 passed`);
  `.venv/bin/python -m py_compile` passed for the touched greenfield UX modules and
  release smoke script.
- 2026-05-08 traceability writer hardening fixed the remaining applied-Radar
  sludge discovered by fresh external-domain temp-repo proof: structured risks,
  questions, dependencies, and release stages now render as complete governed
  bullets instead of fragments like `R1.`, `Q1.`, `domain contract.`, or
  `command.`; question punctuation is preserved; external-domain customization prompts no
  longer split into lowercase fragments. Proof: source-local `greenfield
  propose` produced 270-line project-first text with 24 project-intelligence
  layers, source-local apply wrote all four external-domain Radar workstreams with no
  shallow-fragment hits, `.venv/bin/python -m pytest
  tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_greenfield_intelligence_schema.py
  tests/unit/runtime/test_component_authoring.py
  tests/unit/install/test_local_release_smoke.py -q` passed (`58 passed`), and
  `.venv/bin/python -m py_compile` passed for the touched greenfield modules.
- 2026-05-08 Atlas UX deepening made the default greenfield diagram suite
  act like an architecture review board instead of a box-and-arrow sketch.
  Canonical diagram rows now carry `review_focus`, `operator_question`, and
  `proof_gate`; proposal text renders those fields under `Draft Atlas diagrams`;
  the generated Mermaid sources include evidence-boundary, code-gate,
  decision-lens, state-note, unresolved-risk, and surface-agreement annotations
  directly inside the diagrams. Proof: source-local `greenfield propose` for
  an external-domain fixture rendered 290 lines with per-diagram summary/review/
  question/gate guidance, canonical JSON carried five annotated Atlas rows, and
  `.venv/bin/python -m pytest tests/unit/runtime/test_greenfield_atlas_contract.py
  tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_greenfield_intelligence_schema.py
  tests/unit/runtime/test_component_authoring.py
  tests/unit/install/test_local_release_smoke.py -q` passed (`69 passed`) plus
  `.venv/bin/python -m py_compile` for the touched proposal rendering/scaffold modules.
- 2026-05-08 greenfield anti-slop hardening removed the residual applied-Radar
  weak spots found by a fresh external-domain audit: proposal-level risks are now
  domain-specific structured records with class, severity, trigger,
  early-warning signal, and mitigation; old generic greenfield risk boilerplate
  is rejected before apply; workstream ontology labels are deduplicated and
  validated; malformed generated ownership prose such as `owns Own ...` is
  rejected; parent workstreams use program-level ontology instead of repeating
  child implementation nouns; proposal and applied Radar risk rendering preserve
  the structured risk fields. Proof: `.venv/bin/python -m pytest
  tests/unit/runtime/test_greenfield_atlas_contract.py
  tests/unit/runtime/test_greenfield_host_routing.py
  tests/unit/runtime/test_greenfield_intelligence_schema.py
  tests/unit/runtime/test_greenfield_proposals.py -q` passed (`49 passed`);
  source-local `greenfield propose/create` for an external-domain fixture
  produced 4 workstreams, 3 components, 5 diagrams, 27 domain-intelligence
  fields per workstream, unique ontology labels, project-gated closeout, no
  old boilerplate, no malformed ownership phrase, and component specs with
  Risk Console/Risk Signal Engine/Scenario Replay Harness-specific markers.
- 2026-05-09 preview/write-gate hardening split the default greenfield text
  from the deep accepted record. `greenfield propose` now shows four review
  gates: product interpretation, clarify-before-apply choices, a compact
  workstream/component/architecture preview, and the confirmed-write point.
  The full `--format json` path still carries the deep project/workstream,
  component, architecture, wave, release, risk, validation, and memory record
  that `greenfield create/apply --confirm` validates before Tribunal-gated
  writes. Domain-bearing trailing title terms are preserved instead of clipping
  prompts at dangling prepositions, and default proposal text stays free of
  provider/mode chatter, raw apply-ready metadata, and governance-surface names
  masquerading as product requirements. Proof: `CB-194` plus focused preview,
  show, bundle, Atlas, source-guard, and release-migration
  tests; live source-local repro showed the compact gated preview and `release
  migration-gate --target-version 0.1.15 --json` reported no blockers.
- 2026-05-09 final greenfield guardrail hardening closed two migration-proof
  gaps found while rerunning the product surfaces: stale consumer repair paths
  now no-op in the Odylith product repo, and standalone Registry
  rendering ignores stale runtime snapshots so the browser payload reflects the
  governed source manifest. Proof: a product-repo guard regression test,
  standalone Registry source-manifest precedence test, real `radar refresh`
  proving the source Registry stays at 30 product components with zero external mock
  components, a refreshed migration-observer pass for `operator-cli-contracts`
  plus `browser-surfaces`, and a regenerated Radar, Registry, Atlas, Casebook,
  and Compass shell surface matrix across desktop/mobile headless browser
  viewports with zero console warnings/errors and zero horizontal overflow.
- 2026-05-09 architecture-view title hardening fixed greenfield diagrams that
  repeated the full prompt-derived project title before every view name. The
  scaffold now keeps project identity in intent, slug, summary, and context,
  while diagram titles stay concise and scannable (`System Overview`,
  `First Slice Flow`, `Component Ownership Map`, `Domain State Model`,
  `Validation And Release Topology`, plus domain-specific view names). The
  Tribunal rejects project-title-prefixed diagram titles before confirmed
  writes. Proof: `CB-195`, focused Atlas tests,
  compact preview repro, and source-local Tribunal rejection
  test for prefixed host-authored titles.
- Deepening pass split science/math into targeted subdomains and added fixture
  proof for commerce, SaaS, dashboards, AI assistants, data ingestion, CLI
  libraries, physics simulation, differential-equation solvers, computational
  biology pipelines, formal proof libraries, statistics/econometrics notebooks,
  math education, geospatial climate analysis, ML experiment platforms, and
  calibration workflows. Formal-proof proposals now carry proof
  checker/theorem obligations and explicitly avoid numerical tolerance/random
  seed advice.
- The earlier in-code fit-classification path is superseded for v0.1.13 by
  host reasoning plus Odylith validation. The remaining durable owners are
  proposal rendering, proposal validation, apply safety, program/release
  schema, topology hygiene, and Compass memory.
- Corrective host-reasoning hardening removed the v0.1.13 in-code project
  taxonomy from the proposal-authoring path. Odylith now emits the
  host-reasoning contract, validates accepted proposal shape, requires
  host-authored `mermaid_source` per Atlas draft, rejects duplicate diagram
  bodies, and records accepted proposals into Compass memory only after
  `--confirm`.
- Atlas topology hardening moved the greenfield path away from generic
  star-topology fallback. The host-authored proposal owns the Mermaid source;
  Odylith validates and scaffolds it through the Atlas catalog writer.
- Follow-on proof passed `27` focused greenfield tests, `219` focused
  greenfield/host/CLI tests, `148` bundle/hygiene/governance tests, the `586`
  test engine/host-parity matrix, the `208` test install/migration lifecycle
  matrix, and the `185 passed, 1 skipped` browser matrix. The release migration
  gate reported `ok: true`, `blocked: 0`, and `ungated: 0`.
- v0.1.14 program/release targeting follow-up passed
  `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_greenfield_proposals.py`
  (`15 passed`),
  `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_backlog_authoring.py tests/unit/runtime/test_program_wave_authoring.py tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_release_planning.py tests/unit/install/test_codex_project_assets.py`
  (`118 passed`), and the greenfield CLI help/propose unit slice (`3 passed`).
- v0.1.14 migration proof passed `tests/unit/install/test_migration_runtime.py`
  (`51 passed`), `tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14`
  (`1 passed`), `release migration-gate --target-version 0.1.14 --json`
  (`blocked_manual_migrations: []`), and `git diff --check`.
- v0.1.14 Atlas palette follow-up passed the focused Atlas/greenfield/migration
  tests (`56 passed`), Atlas browser/render tests (`85 passed`), migration and
  registry intelligence tests (`75 passed`), `atlas auto-update --all-stale`
  (`43` diagrams rendered fresh), `atlas render --fail-on-stale` (`43 fresh`,
  `0 stale`), and `git diff --check`. The deterministic palette now treats
  authored Mermaid as topology truth while Atlas owns rendered color, applies
  darker harmonious grouping colors to containers, applies semantic role colors
  to inner nodes across legacy and new diagrams, and keeps the Atlas viewer stage
  pure white.
- The operator-requested decision-color replacement now maps decision/gate/readiness
  semantics to a soft peach/coral bucket. The follow-up rerendered all `43`
  Atlas diagrams from the renderer style fingerprint, proved `0` stale diagrams,
  passed the focused `67` test Atlas/greenfield/migration slice plus `4` Atlas
  browser tests, and kept old amber tokens out of source and generated Atlas
  text assets.
- v0.1.14 post-release greenfield/wave hardening captured `CB-167` and closed
  the fresh-consumer failure path where generated refresh guards could report
  fingerprint reuse over stale Registry/Radar payloads, greenfield apply could
  silently drop proposed waves with no token-overlap children, and wave
  authoring forced hand-edits that the CLI contract forbids. Focused proof now
  covers byte-content refresh fingerprints, `dashboard refresh --force`,
  preserved zero-overlap waves, `program adopt`, `wave assign --adopt`,
  `backlog create --parent/--umbrella`, translated wave assignment errors, and
  non-tautological program next actions.
- v0.1.15 greenfield quality hardening added `proposal_tribunal.py` as a
  deterministic, host-model agnostic pre-write gate for accepted proposals. The
  gate rejects child workstreams without component/diagram/dependency/proof
  topology, candidate components without boundary/interface/dependency/proof
  expectations, diagrams that do not connect to backlog and Registry topology,
  and release/program structures that cannot make Compass visibly useful. Apply
  now batches the visible Radar/Registry/Atlas/Compass refresh after all truth
  writes and Compass memory recording, avoiding repeated partial refreshes on
  the happy path. Focused proof passed `60` adjacent
  greenfield/program/release/component/surface-refresh tests, `65`
  bundle/capability mirror tests, `39` public-bundle/project-asset tests, and
  the Compass/Radar release-target browser smoke.
- 2026-05-14 confirmed-create hardening closed the v0.1.15 general regression
  where confirmed greenfield guidance could push a host model into
  hand-authoring and schema-repairing a hidden proposal payload after Product
  Intent Confirmation. The confirmed path now makes
  `greenfield create --confirm` build the apply-ready proposal inside Odylith,
  keeps `propose --confirm-intent --format json` as an optional review artifact,
  removes hidden `active-proposal.v1.json` from the default flow, and updates
  release smoke to prove the exact fresh-repo journey: show, no-write Product
  Intent JSON, confirmed apply-ready JSON, confirmed create, governed writes,
  and refreshed surfaces. Focused proof passed the greenfield/runtime/browser
  suite, install asset and release-smoke suites, source-local confirmed-create
  repro in a bootstrapped empty repo, Casebook source validation, component
  Registry validation, engine-integrity validation, and `git diff --check`.
- 2026-05-19 confirmed-intent parser hardening fixed the next fail-closed
  regression in the same confirmed-create contract: domain-specific systems that
  legitimately own evidence review, such as a race gearbox `run evidence review
  surface`, must survive Product Intent parsing and Tribunal proposal
  construction instead of being rejected as generic fallback scaffold. The
  guard now rejects the exact fallback trio while accepting project-specific
  evidence-review systems, preserving both sides of the confirmation gate.
  Focused proof passed
  `tests/unit/runtime/test_greenfield_proposals.py::test_confirmed_intent_parser_accepts_domain_specific_evidence_review_surface`,
  `tests/unit/runtime/test_greenfield_proposals.py::test_confirmed_intent_parser_still_rejects_exact_generic_system_scaffold`,
  and
  `tests/unit/test_cli.py::test_greenfield_propose_confirm_intent_json_is_provider_free`
  (`3 passed`).
- 2026-06-03 confirmed-intent completion decomposition moved actor row
  completion, actor label derivation, meta-row rejection, and actor description
  repair into `greenfield_confirmed_actor_completion.py`; the parent
  `greenfield_confirmed_intent_completion.py` now imports that contract and
  reuses shared confirmed-text helpers from `greenfield_confirmed_text.py`
  instead of keeping local utility forks. The parent dropped from 1,374 to 846
  lines, the new actor owner is 449 lines, and a source-level regression test
  pins the actor phase outside the parent. Proof:
  `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_completion.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_actor_completion.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_text.py`;
  `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py
  tests/unit/runtime/test_greenfield_confirmed_repair.py
  tests/unit/runtime/test_greenfield_artifact_language_quality.py` (`21
  passed`); `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_confirmed_intent.py` (`26 passed`); and
  the widened greenfield artifact bundle with confirmed-intent coverage (`93
  passed`).

## Rollout
- Ship in v0.1.14 with B-141 because the user-facing failure is inseparable from consumer-lane host UX hardening: low latency is not enough if empty-repo greenfield prompts dead-end or if accepted proposals fail to show programs, waves, release targets, Registry topology, and Atlas traceability.
- Keep the Odylith CLI proposal request enabled by default and provider-free;
  the active host model performs the reasoning in chat, and any future
  standalone provider-backed enrichment must be explicit.
- Prove empty/thin consumer UX through CLI, host-routing tests, migration-gate coverage, and browser-surface refreshes before release.

## Why Now
The greenfield failure was reported during the consumer-lane hardening pass. Fixing latency while still refusing broad new-project intent, or writing shallow child topology without release/program proof, would preserve speed but regress the product purpose.

## Product View
Odylith should feel like a precise greenfield architecture partner in empty repos: propose useful governance first, never claim source evidence that does not exist, and apply records only after confirmation through the same CLI-owned surfaces used for existing repos.

## Impacted Components
- `domain-intelligence`
- `analysis-engine`
- `radar`
- `registry`
- `atlas`
- `compass`
- `governance-intervention-engine`
- `odylith`

## Interface Changes
- New CLI family: `odylith greenfield propose`.
- New confirmed CLI path: `odylith greenfield create --confirm`.
- Lower-level validated proposal-file path: `odylith greenfield apply --confirm`.
- New CLI path: `odylith program adopt <umbrella> <workstream>` sets the
  reciprocal parent/child topology required before wave assignment.
- `odylith wave assign` accepts `--adopt` for the common orphan-child case.
- `odylith backlog create` accepts `--parent` / `--umbrella` so new children can
  be born under an existing umbrella without hand-editing governed front matter.
- `odylith dashboard refresh` and owned-surface refresh commands accept
  `--force` to bypass generated refresh-guard reuse when an operator needs an
  explicit rerender.
- `odylith show` empty/thin scenarios now point to proposal-first greenfield governance instead of only asking the operator to provide all fields.
- Component registration can record planned consumer components with `user_intent` evidence without claiming source-backed ownership.

## Migration/Compatibility
- Existing consumer repos need no source-truth migration for greenfield behavior. Upgrading to v0.1.14 installs the additive CLI/runtime path, managed guidance, host skill shims, greenfield `0.0.1` default release targeting, program/wave authoring, and Atlas render polish. Existing source-backed governance remains unchanged; greenfield proposals are additive and confirmation-gated.
- v0.1.14 greenfield behavior remains backward compatible: accepted proposals that name a release selector keep using that selector, while omitted selectors default to the first project release `0.0.1`. Apply now creates the umbrella execution-wave program document when child workstreams exist and targets the first wave plus umbrella to the first release so Compass can show program and release power without over-targeting every child workstream.
- v0.1.15 greenfield apply is still confirmation-gated and backward-compatible
  for already-written consumer truth, but newly accepted proposal JSON must meet
  the stricter Tribunal quality bar before Odylith writes source truth. This is
  intentional: missing topology, shallow component ownership, or invisible
  release/program structure should fail before durable governance artifacts are
  created.
- v0.1.15 project-first greenfield UX is additive for consumers. Existing
  greenfield records remain readable, while new proposals add `project_brief`
  direction options and coding-readiness gates before implementation handoff.
  Managed guidance and browser surfaces converge through normal upgrade
  adoption plus dashboard/sync refresh; no consumer source-truth migration is
  required.
- The confirmed-create hardening is additive for consumers. Existing accepted
  greenfield records remain readable; new confirmed greenfield runs stop asking
  hosts to hand-author private proposal JSON and instead route through
  `odylith greenfield create --confirm`. Upgrades refresh managed guidance,
  bundle assets, and browser surfaces; no consumer source-truth migration is
  required.
- One-word `Customer` values are now valid backlog truth. The relaxation is intentionally scoped to Customer only; Problem, Opportunity, Product View, and Success Metrics keep the stronger detail threshold and placeholder rejection.
- Generated refresh-guard caches are versioned to `v2` and include file bytes,
  not only filesystem size/mtime shape. Upgrades from older releases therefore
  cannot reuse stale `v1` cache entries, and same-size source manifest edits
  force the selected surface to rerender. The new `--force` path remains the
  documented manual escape hatch for explicit operator proof.
- Existing greenfield records do not need a destructive migration. The additive
  authoring verbs let orphan children be adopted into an umbrella through CLI
  truth updates, while future greenfield applies preserve every proposed wave
  even when a wave has no confident child-token overlap.
- Migration observer markers for this slice:
  `migration-observer:0.1.13:guidance-and-skills:d8c8ff0d951d`,
  `migration-observer:0.1.13:guidance-and-skills:b6ccbcebbd7c`,
  `migration-observer:0.1.13:operator-cli-contracts:2d60d08c285d`,
  `migration-observer:0.1.13:browser-surfaces:695cf1a55b3d`,
  `migration-observer:0.1.13:browser-surfaces:fcbd8d2ec808`,
  `migration-observer:0.1.13:browser-surfaces:d00ba488e699`,
  `migration-observer:0.1.13:install-managed-assets:4444145d768a`,
  `migration-observer:0.1.13:install-managed-assets:0b654205854a`,
  `migration-observer:0.1.13:install-managed-assets:13d6f64a015b`,
  `migration-observer:0.1.13:guidance-and-skills:b5799cbf748f`,
  `migration-observer:0.1.13:browser-surfaces:bb2be774790f`,
  `migration-observer:0.1.13:install-managed-assets:f400668668ca`,
  `migration-observer:0.1.13:guidance-and-skills:38e6768904a3`,
  `migration-observer:0.1.13:browser-surfaces:da46e2ca9dea`,
  `migration-observer:0.1.13:browser-surfaces:44b8f03ad08b`,
  `migration-observer:0.1.13:install-managed-assets:20dacaa00761`,
  `migration-observer:0.1.13:browser-surfaces:7a832cdde5ae`,
  `migration-observer:0.1.13:browser-surfaces:e7074b845e26`,
  `migration-observer:0.1.13:browser-surfaces:64c67de45d32`,
  `migration-observer:0.1.13:guidance-and-skills:d307d1dee98b`,
  `migration-observer:0.1.13:browser-surfaces:de07c1596960`,
  `migration-observer:0.1.13:install-managed-assets:10f2fe027321`,
  `migration-observer:0.1.13:guidance-and-skills:43e7a7e7b66a`,
  `migration-observer:0.1.13:install-managed-assets:cc92d0a4ee9d`,
  `migration-observer:0.1.13:browser-surfaces:af1a8c005565`,
  `migration-observer:0.1.13:install-managed-assets:0b0c0d1ffef8`,
  `migration-observer:0.1.13:browser-surfaces:c977b656d5a8`,
  `migration-observer:0.1.13:browser-surfaces:ec2ce938e93c`,
  `migration-observer:0.1.13:install-managed-assets:253ccfb23e93`,
  `migration-observer:0.1.13:guidance-and-skills:e854d7e0d9b5`,
  `migration-observer:0.1.13:install-managed-assets:8dc77c50aa92`,
  `migration-observer:0.1.13:public-docs-and-release-guidance:67252caffe8e`,
  `migration-observer:0.1.13:browser-surfaces:8d03362b49b6`,
  `migration-observer:0.1.13:install-managed-assets:84b480bd2eaf`,
  `migration-observer:0.1.13:browser-surfaces:7ca3752b114d`,
  `migration-observer:0.1.13:install-managed-assets:877351c7e794`,
  `migration-observer:0.1.13:install-managed-assets:378a6ed807cc`,
  `migration-observer:0.1.14:guidance-and-skills:5db32f2987ff`,
  `migration-observer:0.1.14:operator-cli-contracts:e1abf985ede6`,
  `migration-observer:0.1.14:install-managed-assets:1d4f10095f9b`,
  `migration-observer:0.1.15:browser-surfaces:0a085ecb8c35`,
  `migration-observer:0.1.15:install-managed-assets:c46b34c03c1d`,
  `migration-observer:0.1.15:browser-surfaces:32f36ad50bff`,
  `migration-observer:0.1.15:install-managed-assets:e1ab4be0a00f`,
  `migration-observer:0.1.15:guidance-and-skills:5ca274eb23df`,
  `migration-observer:0.1.15:public-docs-and-release-guidance:83dd374589cf`,
  `migration-observer:0.1.15:browser-surfaces:23db7fd0ca24`, and
  `migration-observer:0.1.15:install-managed-assets:5291a3c4b08e`, and
  `migration-observer:0.1.15:operator-cli-contracts:a8504a4c60ea`, and
  `migration-observer:0.1.15:guidance-and-skills:64364569b086`,
  `migration-observer:0.1.15:browser-surfaces:f469b98318dc`, and
  `migration-observer:0.1.15:install-managed-assets:765b855989ca`,
  `migration-observer:0.1.15:browser-surfaces:2d3918fcc7c7`, and
  `migration-observer:0.1.15:install-managed-assets:79060c177fba`,
  `migration-observer:0.1.15:guidance-and-skills:0df65445f86d`, and
  `migration-observer:0.1.15:install-managed-assets:a18d34fb8a8f`,
  `migration-observer:0.1.15:browser-surfaces:b4d20ce668d5`, and
  `migration-observer:0.1.15:install-managed-assets:dea842f8c91c`,
  `migration-observer:0.1.15:browser-surfaces:77f6752a8e62`, and
  `migration-observer:0.1.15:install-managed-assets:4590f557c3cd`,
  `migration-observer:0.1.15:operator-cli-contracts:dc5245ee5acc`, and
  `migration-observer:0.1.15:browser-surfaces:7d4664249c0d`,
  `migration-observer:0.1.15:browser-surfaces:5856f117145e`, and
  `migration-observer:0.1.15:install-managed-assets:81414558e1eb`,
  `migration-observer:0.1.15:operator-cli-contracts:918eeb86f16b`, and
  `migration-observer:0.1.15:operator-cli-contracts:77d724bd9906`, and
  `migration-observer:0.1.15:browser-surfaces:6faa5131670e`, and
  `migration-observer:0.1.15:operator-cli-contracts:13e8531fb4af`,
  `migration-observer:0.1.15:guidance-and-skills:4e1cbbef93d2`,
  `migration-observer:0.1.15:operator-cli-contracts:778c1bb05cdd`,
  `migration-observer:0.1.15:operator-cli-contracts:d48cd7f8f9c7`,
  `migration-observer:0.1.15:browser-surfaces:08249609bf09`, and
  `migration-observer:0.1.15:install-managed-assets:a15f59f7ee85`,
  `migration-observer:0.1.15:guidance-and-skills:abed448d6309`,
  `migration-observer:0.1.15:public-docs-and-release-guidance:103ddeb275f7`,
  `migration-observer:0.1.15:browser-surfaces:29459cdc19ba`, and
  `migration-observer:0.1.15:install-managed-assets:7a716e2451f2`.
  These markers cover the deepened greenfield skill guidance, refreshed
  Domain Intelligence Atlas/Registry/Radar browser surfaces, updated managed
  security-and-trust guidance, updated public README/operator/release-note/security
  guidance, the v0.1.15 Compass/Radar/Registry/Casebook browser-surface refresh
  from the deeper greenfield diagram-suite contract, the project-first
  product-requirements wording pass for proposal text, the product-repo source
  guard, and the follow-up repair that rewrites already-poisoned component
  specs, component registry records, Mermaid source diagrams, and architecture
  catalog records toward the inferred project domain instead of internal surface
  or unrelated template labels.
  direction-option/readiness-gate guidance refresh, the engine-integrity
  validator and expanded capability inventory, the canonical project-intelligence
  proposal object and parent Radar persistence, explicit project/workstream
  invalidation rules, first-class workstream scope and owners, component-local
  Registry dossier topology, the anti-slop structured-risk/ontology/ownership
  hardening for applied greenfield Radar, the fail-closed 15-area engine
  activation contract that keeps Greenfield Domain Intelligence command-backed,
  source-anchored, and activation-described in the product capability map, and
  bundled install-managed dashboard copies.
  The latest markers cover the confirmed-intent artifact requirement, the
  prompt-only confirmed-create fail-closed path, and the consumer-facing
  browser/install asset refresh needed so accepted product narration survives
  into generated governance records.
  The 2026-05-18 component-spec and live-narration hardening is assessed under
  `migration-observer:0.1.15:operator-cli-contracts:7086f45abb8e`,
  `migration-observer:0.1.15:browser-surfaces:6d646859699e`, and
  `migration-observer:0.1.15:install-managed-assets:fb949a80a583`. The
  operator contract remains additive and confirmation-gated: hosts still use
  the same greenfield create/apply flow, while the generated records now have
  stronger general-purpose quality constraints before they are trusted. Existing
  consumer source truth remains readable and does not need destructive
  migration; upgraded browser and bundle assets regenerate cleaner Dashboard,
  Radar, Registry, and Atlas surfaces from each repo's own records.
  Existing consumer governance truth remains unchanged; upgrades
  refresh managed guidance/assets and keep proposal writes explicit through
  `odylith greenfield create --confirm`.
  The 2026-05-20 confirmed-create completion and Atlas self-staleness fix is
  assessed under `migration-observer:0.1.15:browser-surfaces:4d81743c447b`.
  Existing consumer truth remains compatible: the change affects future
  confirmed-create generation and regenerated browser surfaces, while existing
  Radar, Registry, Atlas, release, and Compass records stay owned by the
  consumer repo that created them.

- 2026-05-20 confirmed-create completion hardening made confirmation own the
  full governed artifact set instead of surfacing derivable gaps back to the
  operator. `greenfield create --confirm` now routes confirmed proposals through
  a bounded completion gate that fills project posture, backlog risk/security
  posture, component interfaces/dependencies/validation/risks, and Atlas watch
  paths from the accepted intent before rerunning the greenfield Tribunal and
  governed artifact Tribunals. The same pass removed Atlas self-watch paths so
  newly scaffolded diagrams do not become stale by rendering their own catalog,
  SVG, and PNG assets. Proof includes the confirmed-intent/CLI regression tests,
  governed component Tribunal checks, focused greenfield proposal suites, and a
  fresh external consumer create run that produced Radar, Registry, Atlas,
  release, Compass memory, and refreshed shell surfaces end to end without
  storing the external product's domain labels in Odylith governance truth.
- 2026-06-02 post-confirm semantic-render hardening moved the remaining
  first-path action, visible-result, and coordinated-verb cleanup into shared
  domain-neutral grammar and semantic-quality gates. First-path parsing now
  lives in `greenfield_first_path_semantics.py` so semantic rendering stays
  separate from title normalization, release classification, and slop scanning.
  Confirmed create now
  rejects role/action splices, parser debris, activity-shaped actor names,
  framework proof scaffolds, bare outcome nouns, component-boundary boilerplate,
  and finite action drift before Radar workstreams, Registry components, Atlas
  labels, runtime JSON, or project dashboard copy can be written. The
  requester/reviewer case keeps post-result reviewer follow-up out of the
  requester first-slice prose while multi-actor pre-result workflows remain
  intact. Proof: `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_general_artifact_quality.py
  tests/unit/runtime/test_greenfield_component_spec_quality.py
  tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py
  tests/unit/runtime/test_greenfield_component_semantic_contract_quality.py
  tests/unit/runtime/test_greenfield_confirmed_repair.py
  tests/unit/runtime/test_greenfield_artifact_language_quality.py` passed
  (`67 passed`); `.venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed
  (`1 passed`) with the confirmed-create gate under 30 seconds and semantic
  slop checks enabled; `.venv/bin/python -m pytest -q
  tests/integration/runtime/test_project_tab_browser.py` passed (`2 passed`);
  an ad hoc temp-repo create measurement completed in 11.67 seconds with six
  diagrams, no missing assets, and no slop hits.
- 2026-06-03 confirmed-create prewrite-gate decomposition moved semantic model
  completion plus proposal, component, Registry-spec, greenfield Tribunal, and
  governed-artifact Tribunal preflight aggregation into
  `greenfield_confirmed_prewrite_gate.py`. The parent completion orchestrator
  now delegates those checks and stays below the source-size hard threshold
  (`greenfield_confirmed_completion.py`: 1294 to 1192 lines), preserving the
  under-30-second confirmed-create contract while reducing hot-path ownership
  pressure. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_prewrite_gate.py`
  passed; `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_confirmed_repair.py` passed (`3 passed`);
  the broader greenfield artifact-quality bundle passed 94 tests before the
  browser sandbox blocked Chromium launch; rerunning
  `.venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` with browser
  permissions passed (`1 passed in 9.81s`).
- 2026-06-03 confirmed-intent parser decomposition moved internal-system row
  parsing, labeled-role splitting, concise capability expansion, contextual
  system description repair, generic scaffold detection, and public system
  name/description helpers into `greenfield_confirmed_system_rows.py`. The
  confirmed-intent entrypoint now stays focused on file loading, Markdown/JSON
  section parsing, preamble derivation, and validation
  (`greenfield_confirmed_intent.py`: 1535 to 880 lines), while
  `test_greenfield_confirmed_intent.py` pins the system-row owner and the
  parent line-count ceiling. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_system_rows.py`
  passed; `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_confirmed_intent.py` passed (`27 passed`);
  the broader greenfield artifact-quality bundle passed (`95 passed in
  205.10s`).
- 2026-06-03 post-confirm semantic drift decomposition moved contrastive
  domain-drift detection, semantic repetition clustering, generated-artifact
  sentence extraction, intent/component signature building, and semantic
  overlap scoring into `greenfield_post_confirm_semantic_drift.py`. The
  post-confirm completion gate now keeps package orchestration, prewrite
  preview checks, and formatted failure reporting separate from drift-token
  ownership (`greenfield_post_confirm_completion.py`: 1214 to 853 lines), while
  `test_greenfield_general_artifact_quality.py` pins the dedicated owner and
  parent line-count ceiling. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py
  src/odylith/runtime/domain_intelligence/greenfield_post_confirm_semantic_drift.py
  tests/unit/runtime/test_greenfield_general_artifact_quality.py` passed;
  `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_general_artifact_quality.py` passed (`39
  passed in 154.23s`); `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_prewrite_transaction.py` passed (`22
  passed in 108.95s`); the broader greenfield artifact-quality bundle passed
  (`118 passed in 311.35s`); and the escalated Chromium-capable run of
  `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 14.83s`).
- 2026-06-03 post-confirm semantic-alignment decomposition moved semantic model
  shape checks, component/workstream/diagram alignment, rendered Registry spec
  alignment, component ID fallback, and first-release scope checks into
  `greenfield_post_confirm_semantic_alignment.py`. Shared post-confirm list row
  coercion now lives in `greenfield_post_confirm_rows.py`, so the completion
  parent and drift owner no longer carry local `_mapping_rows` clones. The
  package completion parent now stays below the soft source-size limit
  (`greenfield_post_confirm_completion.py`: 853 to 691 lines), and
  `test_greenfield_general_artifact_quality.py` pins the alignment, drift, and
  row-helper ownership boundaries. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py
  src/odylith/runtime/domain_intelligence/greenfield_post_confirm_semantic_drift.py
  src/odylith/runtime/domain_intelligence/greenfield_post_confirm_semantic_alignment.py
  src/odylith/runtime/domain_intelligence/greenfield_post_confirm_rows.py
  tests/unit/runtime/test_greenfield_general_artifact_quality.py` passed;
  `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_general_artifact_quality.py` passed (`39
  passed in 170.88s`); the broader greenfield artifact-quality bundle passed
  (`118 passed in 334.66s`); and the escalated Chromium-capable run of
  `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 11.96s`).
- 2026-06-03 confirmed-intent validation decomposition moved field-threshold
  checks, meta-narration rejection, qualitative intent gap detection,
  progression/outcome scoring, and semantic-overlap term extraction into
  `greenfield_confirmed_intent_validation.py`. The confirmed-intent parser now
  stays focused on file loading, JSON/Markdown normalization, section parsing,
  and preamble derivation (`greenfield_confirmed_intent.py`: 880 to 671
  lines), while `test_greenfield_confirmed_intent.py` pins validation ownership
  and the parser soft-limit ceiling. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_validation.py
  tests/unit/runtime/test_greenfield_confirmed_intent.py` passed;
  `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_confirmed_intent.py` passed (`27 passed in
  41.27s`); the broader greenfield artifact-quality bundle passed (`118 passed
  in 349.90s`); and the escalated Chromium-capable run of `PYTHONPATH=src
  .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 11.79s`).
- 2026-06-03 confirmed-completion quality decomposition moved generic text
  repair detection, sequence repair detection, proof-boundary weakness checks,
  and bad sentence-tail detection into
  `greenfield_confirmed_completion_quality.py`. The confirmed-completion
  orchestrator now calls the shared quality owner instead of carrying local
  `_text_needs_repair`, `_sequence_needs_repair`, and `_has_bad_tail` helpers
  (`greenfield_confirmed_completion.py`: 1192 to 1068 lines), while
  `test_greenfield_confirmed_repair.py` pins the owner split. Proof:
  `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion_quality.py
  tests/unit/runtime/test_greenfield_confirmed_repair.py` passed;
  `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_confirmed_repair.py` passed (`3 passed in
  10.66s`); the broader greenfield artifact-quality bundle passed (`118 passed
  in 332.17s`); and the escalated Chromium-capable run of `PYTHONPATH=src
  .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 11.54s`).
- 2026-06-03 confirmed-completion text-model decomposition moved confirmed-create
  phrase derivation, workstream labels and sentences, component/backlog lexical
  matching, diagram/project title derivation, first-path/proof/state summaries,
  actor summaries, and keyword extraction into
  `greenfield_confirmed_completion_text_model.py`. The completion parent now
  calls that owner directly, removed dead pass-through component wrappers for
  interfaces/dependencies/validation, and dropped below the 800-line soft limit
  (`greenfield_confirmed_completion.py`: 1068 to 793 lines), while
  `test_greenfield_confirmed_repair.py` pins the text-model owner split. Proof:
  `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion_text_model.py
  tests/unit/runtime/test_greenfield_confirmed_repair.py` passed;
  `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_confirmed_repair.py` passed (`3 passed in
  9.95s`); the broader greenfield artifact-quality bundle passed (`118 passed
  in 310.95s`); and `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 10.08s`).
- 2026-06-03 confirmed-component helper cleanup removed the duplicate
  `_title_phrase` definition and unused `_can_clause` helper from
  `greenfield_confirmed_components.py`. The component owner now stays below the
  800-line soft limit (`808` to `792` lines), and
  `test_greenfield_component_spec_quality.py` pins the single title helper,
  absence of the dead clause helper, and soft-limit ceiling. Proof:
  `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_components.py
  tests/unit/runtime/test_greenfield_component_spec_quality.py` passed; focused
  component proof passed with `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_component_spec_quality.py
  tests/unit/runtime/test_greenfield_confirmed_surfaces.py::test_confirmed_greenfield_noun_phrase_responsibilities_stay_grammatical`
  (`9 passed in 0.34s`).
- 2026-06-03 confirmed-backlog text-model decomposition moved Radar
  workstream phrase derivation, actor label extraction, first-action/outcome
  clauses, proof focus selection, problem fallback wording, product-term
  overlap checks, and rationale-line generation into
  `greenfield_confirmed_backlog_text_model.py`. The Radar row builder now
  stays focused on program/release/backlog record assembly
  (`greenfield_confirmed_backlog.py`: 911 to 503 lines), while
  `test_greenfield_artifact_language_quality.py` pins the text-model owner and
  parent soft-limit ceiling. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_backlog.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_backlog_text_model.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_proposal.py
  tests/unit/runtime/test_greenfield_component_spec_quality.py
  tests/unit/runtime/test_greenfield_artifact_language_quality.py` passed;
  focused artifact-language/component proof passed (`15 passed in 3.04s`);
  the broader greenfield artifact-quality bundle passed (`120 passed in
  311.68s`); and `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 10.09s`).
- 2026-06-03 confirmed-Atlas diagram text-model decomposition moved component
  card descriptions, product/actor/proof briefs, proof-review labels,
  workstream title derivation, Mermaid label trimming, and short-label cleanup
  into `greenfield_confirmed_diagram_text.py`. The diagram owner now keeps
  row assembly and flowchart wiring focused (`greenfield_confirmed_diagrams.py`:
  999 to 468 lines), while `test_greenfield_confirmed_diagrams.py` pins the
  text-model owner and parent soft-limit ceiling. The same pass repaired a
  stale confirmed-surface assertion so the test expects the current imperative
  action label `Tap Record` instead of the older third-person label. Proof:
  `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagrams.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagram_text.py
  tests/unit/runtime/test_greenfield_confirmed_diagrams.py
  tests/unit/runtime/test_greenfield_confirmed_surfaces.py` passed; focused
  diagram/surface proof passed (`6 passed in 5.80s`); the broader greenfield
  artifact-quality bundle passed (`126 passed in 388.79s`); and
  `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 14.50s`).
- 2026-06-03 component contract profile decomposition moved the document-context
  and status-view contract builders, profile-specific phrase extraction,
  transition selection, outside-boundary wording, and local proof row generation
  into `greenfield_component_contract_profiles.py`. The component contract
  parent now selects the profile and owns the generic fallback contract without
  carrying specialized profile grammar (`greenfield_component_contract.py`: 952
  to 603 lines), while `test_greenfield_component_spec_quality.py` pins the
  profile owner and parent soft-limit ceiling. Proof: `.venv/bin/python -m
  py_compile
  src/odylith/runtime/domain_intelligence/greenfield_component_contract.py
  src/odylith/runtime/domain_intelligence/greenfield_component_contract_profiles.py
  tests/unit/runtime/test_greenfield_component_spec_quality.py` passed; focused
  component spec and semantic contract proof passed (`10 passed in 0.40s`); the
  broader greenfield artifact-quality bundle passed (`127 passed in 403.37s`);
  and `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 13.49s`).
- 2026-06-03 component semantic-context decomposition moved context-derived
  phrase extraction, late first-path/proof backfill selection, context anchor
  expansion, actor/action prefix removal, and context-backfill decisions into
  `greenfield_component_semantic_context.py`. The semantic contract owner now
  focuses on assembling component-local Registry contracts from accepted product
  facts (`greenfield_component_semantic_contract.py`: 863 to 627 lines), while
  `test_greenfield_component_semantic_contract_quality.py` pins the context
  owner and parent soft-limit ceiling. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_component_semantic_contract.py
  src/odylith/runtime/domain_intelligence/greenfield_component_semantic_context.py
  tests/unit/runtime/test_greenfield_component_semantic_contract_quality.py`
  passed; focused component semantic/spec proof passed (`11 passed in 0.41s`);
  the broader greenfield artifact-quality bundle passed (`128 passed in
  345.24s`); and `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 11.45s`).
- 2026-06-03 component contract target decomposition moved rendered-spec issue
  parsing, repair target selection, duplicate-target dedupe, and
  operator-facing component-spec blocker copy into
  `greenfield_component_contract_targets.py`. The differentiation owner now
  repairs component-local contracts without carrying spec-target parsing
  (`greenfield_component_contract_differentiation.py`: 837 to 772 lines), while
  `test_greenfield_component_spec_quality.py` pins the target owner, parent
  soft-limit ceiling, and concrete issue-to-row mapping. Proof:
  `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_component_contract_differentiation.py
  src/odylith/runtime/domain_intelligence/greenfield_component_contract_targets.py
  src/odylith/runtime/domain_intelligence/greenfield_proposals.py
  src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py
  tests/unit/runtime/test_greenfield_component_spec_quality.py
  tests/unit/runtime/test_greenfield_confirmed_body_comp.py
  tests/unit/runtime/test_greenfield_confirmed_repair.py` passed; focused
  component/prewrite proof passed (`15 passed in 14.63s`); the broader
  greenfield artifact-quality bundle passed (`129 passed in 332.92s`); and
  `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 11.39s`).
- 2026-06-03 apply-prewrite Registry/Atlas decomposition moved first-release
  component input shaping, dry-run Registry component preview, in-memory
  Registry spec rendering, component dependency/risk/responsibility copy, Atlas
  prewrite Mermaid preview, and diagram ID allocation into
  `greenfield_apply_components.py` and `greenfield_apply_diagrams.py`. The
  apply-prewrite parent now owns staged package assembly, release preview,
  accepted-project/Compass preview, and path remapping without carrying
  Registry/Atlas rendering policy (`greenfield_apply_prewrite.py`: 1034 to 459
  lines), while `test_greenfield_prewrite_transaction.py` pins the component
  and diagram owners outside the parent. Proof: `.venv/bin/python -m
  py_compile
  src/odylith/runtime/domain_intelligence/greenfield_apply_prewrite.py
  src/odylith/runtime/domain_intelligence/greenfield_apply_components.py
  src/odylith/runtime/domain_intelligence/greenfield_apply_diagrams.py
  src/odylith/runtime/domain_intelligence/greenfield_proposals.py
  tests/unit/runtime/test_greenfield_prewrite_transaction.py
  tests/unit/runtime/test_greenfield_general_artifact_quality.py
  tests/unit/runtime/test_greenfield_proposals.py` passed; focused prewrite
  proof passed (`25 passed in 124.26s`); the broader greenfield
  artifact-quality bundle passed (`130 passed in 333.90s`); and
  `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 10.93s`).
- 2026-06-03 final apply governed-write decomposition moved Radar file writes,
  stale workstream artifact cleanup, release targeting writes, program
  creation, Atlas scaffold/upsert behavior, Registry component authoring,
  accepted-project memory recording, dashboard refresh, and next-step shaping
  into `greenfield_apply_write.py`. `greenfield_proposals.py` now stays focused
  on no-write intent preview, proposal normalization, prewrite package repair,
  transaction setup, and CLI output (`greenfield_proposals.py`: 676 lines;
  `greenfield_apply_write.py`: 477 lines), while
  `test_greenfield_proposals.py::test_greenfield_apply_write_stays_in_dedicated_owner`
  prevents final writes from returning to the parent. The same proof pass fixed
  a post-confirm semantic alignment edge: blank component `release_scope` now
  means active unless explicitly deferred/out of scope, matching the semantic
  model builder and Registry writer, and apply-time semantic repair can refresh
  stale semantic models before the gate runs. Proof: `.venv/bin/python -m
  py_compile
  src/odylith/runtime/domain_intelligence/greenfield_apply_semantic.py
  src/odylith/runtime/domain_intelligence/greenfield_apply_write.py
  src/odylith/runtime/domain_intelligence/greenfield_post_confirm_semantic_alignment.py
  src/odylith/runtime/domain_intelligence/greenfield_proposals.py
  tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_greenfield_prewrite_transaction.py
  tests/unit/runtime/test_greenfield_general_artifact_quality.py` passed;
  focused final-apply proof passed (`68 passed in 141.47s`); the broader
  greenfield artifact-quality bundle passed (`130 passed in 331.45s`); and
  `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/integration/runtime/test_greenfield_create_performance.py` passed (`1
  passed in 11.41s`).
- 2026-06-03 first-path clause-renderer decomposition moved generated
  action/capability/outcome clause rendering, visible-result cleanup, trivial
  start detection, and action-chain grammar into
  `greenfield_first_path_clauses.py`; shared typed records now live in
  `greenfield_first_path_types.py`. `greenfield_first_path_semantics.py` now
  owns first-path parsing and model extraction only (`1054` to `358` lines),
  while the clause owner is `734` lines and the type owner is `27` lines.
  `test_greenfield_post_confirm_slop_regressions.py::test_first_path_clause_rendering_stays_in_dedicated_owner`
  pins the owner boundary. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_first_path_semantics.py
  src/odylith/runtime/domain_intelligence/greenfield_first_path_clauses.py
  src/odylith/runtime/domain_intelligence/greenfield_first_path_types.py
  src/odylith/runtime/domain_intelligence/greenfield_semantic_quality.py
  tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py`
  passed; first-path slop proof passed (`14 passed in 2.73s`); broader
  artifact-quality proof passed (`61 passed in 174.67s`); the full
  confirmed-greenfield regression bundle passed (`131 passed in 322.94s`);
  and confirmed-create performance proof passed (`1 passed in 10.11s`).
- 2026-06-03 Tribunal substance-gate decomposition moved confirmed generated
  Radar thinness checks, Registry component-contract substance checks,
  cross-axis proof leakage checks, Atlas scaffold-node checks, first-path
  tail-preservation checks, and first-boundary routing checks into
  `proposal_tribunal_substance.py`. `proposal_tribunal.py` now stays focused
  on deterministic adjudication orchestration, release/program topology,
  backlog/component/diagram traceability, domain security posture, and visible
  Tribunal actors (`972` to `522` lines), while the substance owner is `466`
  lines. `test_greenfield_general_artifact_quality.py::test_greenfield_tribunal_substance_gate_stays_in_dedicated_owner`
  pins the owner boundary. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/proposal_tribunal.py
  src/odylith/runtime/domain_intelligence/proposal_tribunal_substance.py
  tests/unit/runtime/test_greenfield_general_artifact_quality.py` passed;
  focused Tribunal proof passed (`5 passed in 10.58s`); broader
  artifact-quality proof passed (`62 passed in 165.34s`); full
  confirmed-greenfield regression proof passed (`132 passed in 315.92s`); and
  confirmed-create performance proof passed (`1 passed in 9.77s`).
- 2026-06-03 confirmed-intent system-completion decomposition moved internal
  system row completion, fallback system generation, system label cleanup,
  state-label extraction, and context-clause matching into
  `greenfield_confirmed_system_completion.py`. The confirmed-intent completion
  parent now stays focused on orchestration, core-field completion, product
  posture, title repair, and first-path/proof wording (`846` to `646` lines),
  while the system-completion owner is `228` lines.
  `test_greenfield_confirmed_intent.py::test_confirmed_intent_system_completion_stays_in_dedicated_owner`
  pins the owner boundary. Proof: `.venv/bin/python -m py_compile
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_completion.py
  src/odylith/runtime/domain_intelligence/greenfield_confirmed_system_completion.py
  tests/unit/runtime/test_greenfield_confirmed_intent.py` passed; focused
  confirmed-intent proof passed (`28 passed in 39.53s`); broader
  artifact-quality proof passed (`90 passed in 225.71s`); full
  confirmed-greenfield regression proof passed (`133 passed in 341.80s`); and
  confirmed-create performance proof passed (`1 passed in 12.05s`).
- 2026-06-03 Atlas first-path step derivation decomposition moved semantic
  event extraction, launcher-only filtering, first-path step fallback,
  compound-step expansion, and step dedupe into `greenfield_sequence_steps.py`.
  `greenfield_sequence_diagram.py` now owns participant routing, component
  routing, Mermaid labels, and diagram rendering only (`868` to `701` lines),
  while the new step owner is `199` lines. The same pass hardened accepted
  first paths whose final user decision includes `act later` so the Atlas tail
  preservation gate still sees the final action, and kept short
  role-qualified Registry artifacts such as `person follow list` intact in
  generated component contracts. Proof: focused diagram/sequence proof passed
  (`11 passed, 36 deselected in 29.77s`); full confirmed-greenfield proof
  passed (`48 passed in 69.77s`); broader artifact-quality proof passed (`98
  passed in 244.93s`); and confirmed-create performance proof passed (`1
  passed in 12.44s`).

## Test Strategy
- Run focused unit tests for domain intelligence, host routing, component
  authoring, CLI dispatch, show capabilities, and Compass transaction filtering
  with the repo-local interpreter, for example `.venv/bin/python -m pytest -q
  tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py
  tests/unit/runtime/test_greenfield_component_spec_quality.py`.
- For confirmed-create speed and artifact quality, run `.venv/bin/python -m
  pytest -q tests/integration/runtime/test_greenfield_create_performance.py`;
  it must stay under 30 seconds after confirmation and reject generated
  semantic slop in the create payload.
- Run governance validators for Casebook, backlog, plan binding/traceability as
  touched, release migration gate, and refreshed Radar/Registry/Atlas/Compass
  surfaces.
- Run headless browser smoke over the regenerated dashboards so the new records
  and the timeline-audit fix are visible without layout regressions.

## Open Questions
- Should a future signed domain-pack marketplace augment host reasoning with
  curated evidence, examples, and validators after v0.1.14 ships the open-world
  host-reasoned baseline?
