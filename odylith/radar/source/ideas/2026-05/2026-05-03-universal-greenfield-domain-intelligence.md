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
- 2026-06-04 Atlas sequence-step label-term follow-through moved
  launcher-only and numbered-step display word counts in
  `greenfield_sequence_steps.py` onto `greenfield_domain_term_index.label_terms`.
  The sequence step owner still owns semantic event extraction, fallback
  splitting, compound expansion, and dedupe, but it no longer carries local
  raw word-count regexes for Atlas first-path step filtering. Touched files
  remain below limits (`greenfield_sequence_steps.py`: 200 lines;
  `greenfield_domain_term_index.py`: 131 lines;
  `test_greenfield_confirmed_diagrams.py`: 202 lines). Proof: syntax proof
  passed for the touched modules and test; focused confirmed-diagrams proof
  passed (`5 passed in 0.06s`); wider greenfield artifact proof passed (`162
  passed in 192.91s`); and confirmed-create performance proof passed (`1
  passed in 9.52s`), preserving the under-30s create gate.
- 2026-06-04 confirmed Atlas proof-label word-count follow-through moved
  semantic proof checkpoint and proof-review clause thresholds in
  `greenfield_confirmed_diagram_text.py` onto
  `greenfield_confirmed_text.word_count`. The confirmed diagram text owner
  still owns proof-label cleanup, proof-review label selection, Mermaid label
  trimming, and short-label cleanup, but confirmed text now owns Markdown
  cleanup and visible word counting for Atlas proof labels. Touched files
  remain below limits (`greenfield_confirmed_diagram_text.py`: 544 lines;
  `greenfield_confirmed_text.py`: 399 lines;
  `test_greenfield_confirmed_diagrams.py`: 215 lines). Proof: syntax proof
  passed for the touched modules and test; focused confirmed-diagrams proof
  passed (`5 passed in 0.06s`); wider greenfield artifact proof passed (`162
  passed in 193.46s`); and confirmed-create performance proof passed (`1
  passed in 9.56s`), preserving the under-30s create gate.
- 2026-06-03 artifact-enrichment graph and Tribunal actor decomposition moved
  Domain Intelligence graph normalization into `artifact_graph.py` and visible
  Tribunal actor projection into `artifact_tribunal_actors.py`.
  `artifact_enrichment.py` now owns artifact projections only (`843` to `228`
  lines), while the graph owner is `180` lines and the actor owner is `465`
  lines. `test_greenfield_proposals.py::test_artifact_enrichment_graph_and_tribunal_actors_stay_in_dedicated_owners`
  pins the owner boundary and public export list. Proof: syntax proof passed
  for touched Domain Intelligence and project-intelligence modules; focused
  projection proof passed (`13 passed, 74 deselected in 13.48s`); standard
  greenfield artifact-quality proof passed (`143 passed in 235.82s`); and
  confirmed-create performance proof passed (`1 passed in 11.44s`).
- 2026-06-03 confirmed project-brief decomposition moved project-brief
  generation and host-independent command handoff text into
  `greenfield_confirmed_project_brief.py`, and consolidated greenfield command
  quoting in `greenfield_command_text.py`. `greenfield_confirmed_components.py`
  now owns Registry component generation only (`792` to `581` lines), while
  the project-brief owner is `249` lines and the command-text owner is `10`
  lines. `test_greenfield_component_spec_quality.py::test_confirmed_project_brief_stays_in_dedicated_owner`
  pins the owner boundary and single shell-quote owner. Proof: syntax proof
  passed for touched component, project-brief, proposal, rendering, and review
  card modules; focused component/proposal proof passed (`60 passed in
  21.26s`); standard greenfield artifact-quality proof passed (`144 passed in
  238.94s`); and confirmed-create performance proof passed (`1 passed in
  11.48s`).
- 2026-06-03 component contract phrase-owner consolidation moved natural short
  list rendering into `greenfield_component_terms.py` and migrated base
  component contracts, semantic contracts, and contract differentiation away
  from local `_term_phrase`, `_phrase`, and `_content_terms` clones. The shared
  terms owner now exports `natural_phrase` beside the existing comma-clause
  `phrase`, while `greenfield_component_contract_differentiation.py` uses
  `domain_terms` for fallback contract term filtering (`772` to `755` lines);
  `greenfield_component_contract.py` is `593` lines,
  `greenfield_component_semantic_contract.py` is `626` lines, and
  `greenfield_component_terms.py` remains below the soft limit at `779` lines.
  `test_greenfield_component_spec_quality.py::test_component_contract_phrase_helpers_stay_in_terms_owner`
  pins the owner boundary and formatter behavior. Proof: syntax proof passed
  for the touched component-contract and test modules; focused component-spec
  proof passed (`12 passed in 0.23s`); standard greenfield artifact-quality
  proof passed (`145 passed in 243.87s`); and confirmed-create performance
  proof passed (`1 passed in 11.93s`).
- 2026-06-03 confirmed component-completion decomposition moved Registry
  component row completion, contract normalization, component field weakness
  checks, component risk enrichment, and component sentence repair into
  `greenfield_confirmed_component_completion.py`. The confirmed completion
  parent now owns the repair loop, project/backlog/diagram completion, prewrite
  issue repair, and release-validation language only (`793` to `592` lines),
  while the component-completion owner is `248` lines.
  `test_greenfield_confirmed_repair.py::test_confirmed_completion_prewrite_gate_stays_in_dedicated_owner`
  now pins the component owner boundary and keeps contract-derived component
  copy out of the parent. Proof: syntax proof passed for the touched confirmed
  completion modules; focused confirmed-repair proof passed (`3 passed in
  10.34s`); focused component-risk/watch-path proof passed (`1 passed in
  3.92s`); standard greenfield artifact-quality proof passed (`145 passed in
  234.45s`); and confirmed-create performance proof passed (`1 passed in
  11.48s`).
- 2026-06-03 row-coercion ownership consolidation promoted shared generated
  list-row coercion into `greenfield_rows.py` and removed local
  `_mapping_rows` clones from confirmed prewrite gating, the deterministic
  Tribunal, confirmed title repair, apply-prewrite remapping, and post-confirm
  semantic/package checks. The former post-confirm-specific row owner was
  deleted instead of left as a wrapper, so row coercion is no longer coupled to
  one package phase (`greenfield_rows.py`: 12 lines;
  `greenfield_post_confirm_completion.py`: 693 lines;
  `proposal_tribunal.py`: 519 lines; `greenfield_apply_prewrite.py`: 456
  lines). `tests/unit/runtime/test_greenfield_row_coercion.py` now pins the
  shared owner and prevents private `_mapping_rows` helpers from returning.
  Proof: syntax proof passed for the touched Domain Intelligence modules and
  row-owner tests; focused row-owner proof passed (`1 passed in 0.02s`);
  focused post-confirm/Tribunal structural proof passed (`2 passed, 38
  deselected in 0.21s`); standard greenfield artifact-quality proof passed
  (`146 passed in 232.66s`); and confirmed-create performance proof passed (`1
  passed in 11.42s`).
- 2026-06-03 dict-row and count follow-through added `dict_rows`,
  `row_count`, and `mapping_count` to the same shared row owner and removed
  duplicate `_dict_rows`, `_row_count`, and `_mapping_count` clones from
  confirmed completion, confirmed prewrite gating, and post-confirm package
  reporting. Mutable generated rows and package artifact counts now share the
  same row-coercion contract as mapping rows (`greenfield_rows.py`: 30 lines;
  `greenfield_confirmed_completion.py`: 587 lines;
  `greenfield_confirmed_prewrite_gate.py`: 118 lines;
  `greenfield_post_confirm_completion.py`: 687 lines), and
  `tests/unit/runtime/test_greenfield_row_coercion.py` prevents private row
  coercion and count helpers from returning. Proof: syntax proof passed for
  the touched row/completion/prewrite/post-confirm modules; focused
  row/post-confirm proof passed (`3 passed, 38 deselected in 4.98s`);
  standard greenfield artifact-quality proof passed (`146 passed in
  235.23s`); and confirmed-create performance proof passed (`1 passed in
  11.63s`).
- 2026-06-03 row-owner and semantic-copy follow-through routed remaining
  component, backlog, handoff, created-row, proposal-row, and wave-row readers
  through `greenfield_rows.py` instead of package-local `_component_rows` or
  `_created_rows` helpers. The same pass hardened confirmed project-brief and
  Registry semantic-context text so metadata-led actor/action phrases such as
  `resident create repair request` and ditransitive copy such as `shows the
  resident a confirmation` do not leak into generated component contracts or
  project posture. Touched owners stay below the soft limit
  (`greenfield_backlog_impact.py`: 156 lines;
  `greenfield_component_contract_differentiation.py`: 749 lines;
  `greenfield_confirmed_component_completion.py`: 242 lines;
  `greenfield_confirmed_project_brief.py`: 263 lines;
  `greenfield_component_semantic_context.py`: 308 lines;
  `greenfield_experience.py`: 473 lines). Proof: syntax proof passed for all
  touched modules; focused row/component artifact proof passed (`59 passed in
  164.10s`); the two exposed post-confirm slop regressions passed (`2 passed
  in 1.15s`); broad confirmed-greenfield proof passed (`160 passed in
  239.60s`); and confirmed-create performance proof passed (`1 passed in
  11.51s`).
- 2026-06-03 confirmed-intent text-list follow-through moved duplicate
  `_strings` helpers from the parser, completion, actor completion, system
  completion, and validation modules into `greenfield_confirmed_text.py` as
  `confirmed_text_values`. Confirmed list fields now share one strict
  str-or-sequence cleaner for Markdown marker removal while preserving the
  no-mapping-flattening contract of accepted intent records. The moved callers
  stay below the source soft limit (`greenfield_confirmed_text.py`: 356 lines;
  `greenfield_confirmed_intent.py`: 666 lines;
  `greenfield_confirmed_intent_completion.py`: 643 lines;
  `greenfield_confirmed_actor_completion.py`: 445 lines;
  `greenfield_confirmed_system_completion.py`: 226 lines;
  `greenfield_confirmed_intent_validation.py`: 249 lines), and the new
  enforcement test lives in a focused 32-line test file instead of growing the
  oversized confirmed-intent fixture suite. Proof: syntax proof passed for all
  touched modules; focused confirmed-text/intent proof passed (`29 passed in
  39.80s`); broad confirmed-greenfield proof passed (`160 passed in
  240.87s`); and confirmed-create performance proof passed (`1 passed in
  11.52s`).
- 2026-06-04 confirmed project-surface word-count follow-through moved
  project-brief and project-intelligence shallow-row checks onto
  `greenfield_confirmed_text.word_count`. The project brief and project
  intelligence validators now keep schema/row requirements while the confirmed
  text owner handles Markdown cleanup and visible word counting, removing the
  local `_word_count` helpers from both generated project-surface validators.
  Touched files remain below limits (`greenfield_confirmed_text.py`: 399 lines;
  `greenfield_project_brief.py`: 254 lines;
  `greenfield_project_intelligence.py`: 200 lines;
  `test_greenfield_confirmed_text.py`: 102 lines). Proof: syntax proof passed
  for the touched modules and test; focused confirmed-text/project-surface proof
  passed (`5 passed in 0.21s`); wider greenfield artifact proof passed (`160
  passed in 195.36s`); and confirmed-create performance proof passed (`1 passed
  in 9.59s`), preserving the under-30s create gate.
- 2026-06-04 confirmed-intent parser word-count follow-through moved accepted
  intent section inference onto `greenfield_confirmed_text.word_count`. The
  parser still owns Markdown/JSON section parsing, preamble paragraph
  selection, and story/state/path/proof derivation, but confirmed text owns
  Markdown cleanup plus visible word counting, removing the parser-local
  `_word_count` helper and the last confirmed parser fork in this slice.
  Touched files remain below limits (`greenfield_confirmed_intent.py`: 663
  lines; `greenfield_confirmed_text.py`: 399 lines;
  `test_greenfield_confirmed_text.py`: 117 lines). Proof: syntax proof passed
  for the touched modules and test; focused confirmed-intent proof passed (`32
  passed in 32.52s`); wider greenfield artifact proof passed (`161 passed in
  196.16s`); and confirmed-create performance proof passed (`1 passed in
  9.60s`), preserving the under-30s create gate.
- 2026-06-03 greenfield coercion hygiene follow-through removed the remaining
  workstream-local `_list_values` clone and the project-binding-local
  `_mapping` clone from the B-142/CB-202 slice. Workstream Domain Intelligence
  validation and rendering now use the shared `greenfield_text.text_values`
  owner directly, while project-intelligence artifact binding uses
  `runtime.common.value_coercion.mapping_copy` for root and release-plan
  mapping coercion. `tests/unit/runtime/test_greenfield_coercion_hygiene.py`
  pins both owner boundaries so future artifact-quality fixes cannot re-add
  private list or mapping coercion in those modules. Proof: focused
  coercion/domain-intelligence/project-binding proof passed (`49 passed in
  16.10s`); broader greenfield artifact-quality and confirmed-create proof
  passed (`119 passed in 233.71s`), including the under-30s confirmed-create
  performance gate.
- 2026-06-03 project-brief rendering ownership follow-through moved proposal
  text rendering for the top-level `project_brief` into
  `greenfield_project_brief.py`. `proposal_rendering.py` now delegates through
  `render_project_brief_lines` instead of owning `_project_brief_lines`,
  blueprint-section, customization-option, checkpoint, or host-path helpers,
  and the project-brief owner uses shared `greenfield_rows.mapping_rows` for
  mixed generated rows. Touched files stay small (`proposal_rendering.py`: 573
  lines; `greenfield_project_brief.py`: 257 lines; enforcement test: 88
  lines). Proof: syntax proof passed for the touched renderer modules and test;
  focused project-brief/proposal proof passed (`4 passed in 0.22s`); broader
  proposal and artifact-quality proof passed (`87 passed in 189.11s`); and
  confirmed-create performance proof passed (`1 passed in 11.97s`), preserving
  the under-30s create gate.
- 2026-06-03 component-axis term-helper follow-through removed the remaining
  `_content_terms`, `_term_token`, `_phrase`, and `_normalize_axis_text`
  helpers from `greenfield_component_axes.py`. Derived Registry semantic axes
  now use `greenfield_component_terms.domain_terms` and the shared
  space-joined `term_phrase` helper, so axis keys, component contracts, and
  artifact-quality checks share the same component-term owner instead of
  drifting through a local fork. Touched files remain below the soft limit
  (`greenfield_component_axes.py`: 148 lines; `greenfield_component_terms.py`:
  784 lines; `test_greenfield_component_spec_quality.py`: 364 lines). Proof:
  syntax proof passed for the touched modules and test; focused component-axis
  and spec-quality proof passed (`15 passed in 13.16s`); broad component and
  artifact-quality proof passed (`54 passed in 166.71s`); and confirmed-create
  performance proof passed (`1 passed in 11.73s`), preserving the under-30s
  create gate.
- 2026-06-04 component contract field phrase-helper follow-through removed the
  remaining local `_phrase` helper from
  `greenfield_component_contract_fields.py`. Supporting-artifact text now calls
  the shared comma-clause `greenfield_component_terms.phrase` helper, so
  component axis derivation, component contracts, contract differentiation, and
  field-level support-artifact wording share the same component-term owner.
  Touched files remain below the soft limit
  (`greenfield_component_contract_fields.py`: 450 lines;
  `greenfield_component_terms.py`: 784 lines;
  `test_greenfield_component_spec_quality.py`: 370 lines). Proof: syntax proof
  passed for the touched modules and test; focused component-spec proof passed
  (`12 passed in 0.24s`); broad component and artifact-quality proof passed
  (`54 passed in 170.39s`); and confirmed-create performance proof passed
  (`1 passed in 13.04s`), preserving the under-30s create gate.
- 2026-06-04 component term-index ownership follow-through moved ordered
  component-local term extraction out of the Registry quality gate and into
  `greenfield_component_term_index.py`. Component contracts, contract
  differentiation, component terms, and component quality gates now import
  `ordered_domain_terms` from the dedicated term-index owner instead of
  reaching through `greenfield_component_contract_quality.py`, so Registry
  quality checks no longer hide the reusable term extraction owner. Touched
  files remain below the soft limit (`greenfield_component_term_index.py`: 105
  lines; `greenfield_component_contract_quality.py`: 588 lines;
  `greenfield_component_terms.py`: 784 lines;
  `test_greenfield_component_spec_quality.py`: 391 lines). Proof: syntax proof
  passed for the touched modules and test; focused component-spec proof passed
  (`12 passed in 0.22s`); broad component and artifact-quality proof passed
  (`54 passed in 152.75s`); and confirmed-create performance proof passed
  (`1 passed in 9.95s`), preserving the under-30s create gate.
- 2026-06-04 greenfield domain-term index follow-through split shared
  artifact specificity tokenization into `greenfield_domain_term_index.py`.
  Product-risk genericity checks now use `ordered_terms` with risk-specific
  stopwords instead of a local `_domain_terms` helper, and the component-term
  index delegates tokenization to the same shared kernel while keeping
  component-specific stopwords. This keeps Radar product-risk specificity and
  Registry component term matching on one host/model/project-agnostic term
  normalization path. Touched files remain below limits
  (`greenfield_domain_term_index.py`: 46 lines;
  `greenfield_component_term_index.py`: 84 lines;
  `greenfield_product_risks.py`: 555 lines;
  `test_greenfield_proposals.py`: 1391 lines). Proof: syntax proof passed
  for the touched modules and test; focused proposal proof passed
  (`46 passed in 15.79s`); focused component proof passed
  (`12 passed in 0.23s`); broad artifact/proposal proof passed
  (`100 passed in 176.18s`); and confirmed-create performance proof passed
  (`1 passed in 11.47s`), preserving the under-30s create gate.
- 2026-06-04 Registry spec term-distinctiveness follow-through moved
  component-domain term sets, section-term filtering, and component-local
  distinctiveness scoring into `greenfield_component_term_index.py`.
  `greenfield_component_contract_quality.py` now decides quality failures by
  calling `component_domain_terms`, `section_domain_terms`, and
  `component_local_terms` instead of owning `domain_terms`, `_section_terms`,
  or `_local_domain_terms`. This keeps generated Registry spec quality checks
  on the same component-term index owner as contracts, component terms, and
  contract differentiation while keeping the quality gate focused on
  fail-closed decisions. Touched files remain below limits
  (`greenfield_component_term_index.py`: 128 lines;
  `greenfield_component_contract_quality.py`: 538 lines;
  `test_greenfield_component_spec_quality.py`: 417 lines). Proof: syntax
  proof passed for the touched modules and test; focused component-spec proof
  passed (`12 passed in 0.24s`); broad artifact/proposal proof passed
  (`128 passed in 222.27s`); and confirmed-create performance proof passed
  (`1 passed in 11.39s`), preserving the under-30s create gate.
- 2026-06-04 confirmed-intent semantic-term follow-through moved validation
  and internal-system semantic token extraction into
  `greenfield_confirmed_text.semantic_terms`. Confirmed-intent validation now
  passes `CONFIRMED_INTENT_VALIDATION_STOPWORDS` into the shared text owner
  instead of carrying its own `_TERM_STOPWORDS` and `_semantic_terms` loop, and
  `greenfield_confirmed_system_rows.py` imports the same owner instead of
  normalizing tokens locally. The pass also split ownership and parser tests
  into `test_greenfield_confirmed_intent_ownership.py`, bringing
  `test_greenfield_confirmed_intent.py` back below the test ceiling. Touched
  files remain below limits (`greenfield_confirmed_text.py`: 398 lines;
  `greenfield_confirmed_intent_validation.py`: 197 lines;
  `greenfield_confirmed_system_rows.py`: 693 lines;
  `test_greenfield_confirmed_text.py`: 61 lines;
  `test_greenfield_confirmed_intent.py`: 1459 lines;
  `test_greenfield_confirmed_intent_ownership.py`: 269 lines). Proof: syntax
  proof passed for the touched modules and tests; focused confirmed-intent
  proof passed (`30 passed in 37.40s`); broad artifact/proposal proof passed
  (`130 passed in 204.69s`); and confirmed-create performance proof passed
  (`1 passed in 9.91s`), preserving the under-30s create gate.
- 2026-06-04 Atlas sequence term-routing follow-through moved first-path
  sequence and flowchart component matching onto
  `greenfield_domain_term_index.ordered_terms`. The shared term index now
  supports caller-owned `stem_ing=True` for sequence routing that needs the
  previous gerund collapse, while `greenfield_sequence_diagram.py` keeps only
  sequence-specific stopwords and no longer imports `normalize_domain_token` or
  owns `_domain_terms`. Touched files remain below limits
  (`greenfield_domain_term_index.py`: 54 lines;
  `greenfield_sequence_diagram.py`: 695 lines;
  `test_greenfield_confirmed_diagrams.py`: 189 lines). Proof: syntax proof
  passed for the touched modules and test; focused diagram proof passed
  (`5 passed in 0.05s`); wider artifact/proposal proof passed
  (`105 passed in 166.48s`); and confirmed-create performance proof passed
  (`1 passed in 9.90s`), preserving the under-30s create gate.
- 2026-06-04 semantic-model term-index follow-through moved generated semantic
  model ontology terms, required-field terms, event-target terms, and actor
  terms onto `greenfield_domain_term_index.ordered_terms`.
  `greenfield_semantic_model.py` now owns only semantic-model stopwords and no
  longer imports `normalize_domain_token` or defines `_semantic_terms`, keeping
  generated Radar, Registry, Atlas, and Tribunal semantic model vocabulary on
  the same shared normalization owner as product risks and Atlas sequence
  routing. Touched files remain below limits
  (`greenfield_semantic_model.py`: 494 lines;
  `test_greenfield_intelligence_schema.py`: 111 lines). Proof: syntax proof
  passed for the touched module and test; focused intelligence-schema proof
  passed (`3 passed in 0.11s`); wider artifact/proposal/post-confirm proof
  passed (`108 passed in 168.60s`); and confirmed-create performance proof
  passed (`1 passed in 9.91s`), preserving the under-30s create gate.
- 2026-06-04 post-confirm drift term-index follow-through moved semantic
  repetition signatures, overlap signatures, and contrastive drift term
  signatures onto `greenfield_domain_term_index.ordered_terms`.
  `greenfield_post_confirm_semantic_drift.py` now owns only post-confirm
  stopwords and separator cleanup, and no longer imports
  `normalize_domain_token` or loops over regex tokens locally. The enforcement
  guard lives in a dedicated small test instead of growing the oversized
  aggregate artifact-quality suite. Touched files remain below limits
  (`greenfield_post_confirm_semantic_drift.py`: 389 lines;
  `test_greenfield_semantic_drift_terms.py`: 32 lines). Proof: syntax proof
  passed for the touched module and test; focused drift proof passed
  (`2 passed in 0.11s`); wider artifact/proposal/post-confirm proof passed
  (`101 passed in 164.28s`); and confirmed-create performance proof passed
  (`1 passed in 9.69s`), preserving the under-30s create gate.
- 2026-06-04 confirmed-artifact Tribunal term-index follow-through moved
  confirmed Radar substance terms, Registry proof-boundary terms, and Atlas
  first-path tail terms onto `greenfield_domain_term_index.ordered_terms`.
  `proposal_tribunal_substance.py` now owns only Tribunal-specific stopwords
  and Atlas action aliases, and no longer imports `normalize_domain_token` or
  loops over regex tokens locally. The enforcement guard lives in a dedicated
  small test instead of growing the oversized aggregate artifact-quality suite.
  Touched files remain below limits (`proposal_tribunal_substance.py`: 461
  lines; `test_greenfield_tribunal_term_index.py`: 31 lines). Proof: syntax
  proof passed for the touched module and test; focused Tribunal proof passed
  (`4 passed in 6.89s`); wider artifact/proposal/post-confirm proof passed
  (`102 passed in 162.96s`); and confirmed-create performance proof passed
  (`1 passed in 9.68s`), preserving the under-30s create gate.
- 2026-06-04 confirmed-artifact Tribunal accepted-term follow-through moved
  accepted public-text product phrase matching onto
  `greenfield_domain_term_index.label_terms`. `proposal_tribunal_substance.py`
  still owns Tribunal scaffold repetition policy and generated-artifact
  substance decisions, but it no longer carries a local accepted-term regex for
  the `evidence record` and `reviewer decision` product-phrase exceptions.
  Touched files remain below limits (`proposal_tribunal_substance.py`: 462
  lines; `greenfield_domain_term_index.py`: 131 lines;
  `test_greenfield_tribunal_term_index.py`: 41 lines). Proof: syntax proof
  passed for the touched modules and test; focused Tribunal term-index proof
  passed (`1 passed in 0.02s`); wider greenfield artifact proof passed (`162
  passed in 193.53s`); and confirmed-create performance proof passed (`1
  passed in 9.54s`), preserving the under-30s create gate.
- 2026-06-04 semantic-quality release-scope term-index follow-through moved
  release-scope and scope-context term signatures onto
  `greenfield_domain_term_index.ordered_terms`. The shared term index now
  supports caller-owned exact aliases and prefix aliases so semantic quality can
  preserve reminder and sharing vocabulary folding while
  `greenfield_semantic_quality.py` owns only release-scope stopwords, alias
  policy, and release-scope decisions. It no longer imports
  `normalize_domain_token` or loops over regex tokens locally. The enforcement
  guard lives in a dedicated small test instead of growing the oversized
  aggregate artifact-quality suite. Touched files remain below limits
  (`greenfield_domain_term_index.py`: 87 lines;
  `greenfield_semantic_quality.py`: 478 lines;
  `test_greenfield_semantic_quality_terms.py`: 47 lines). Proof: syntax proof
  passed for the touched modules and test; focused semantic-quality proof passed
  (`1 passed in 0.03s`) and the health-tracking release-scope scenario passed
  (`1 passed in 3.59s`); wider artifact/proposal/post-confirm proof passed
  (`111 passed in 162.71s`); and confirmed-create performance proof passed
  (`1 passed in 9.67s`), preserving the under-30s create gate.
- 2026-06-04 semantic-quality raw-token follow-through moved sentence-overlap
  n-gram extraction and scoped-clause word counts onto
  `greenfield_domain_term_index.label_terms`. `greenfield_semantic_quality.py`
  now keeps release-scope decisions, sentence-overlap policy, and stopword
  choices while the shared term-index owner handles raw token extraction for
  both semantic and visible-label callers. This removes the remaining
  `re.findall` token loops from the semantic-quality gate without changing
  normalized release-scope term policy. Touched files remain below limits
  (`greenfield_domain_term_index.py`: 131 lines;
  `greenfield_semantic_quality.py`: 475 lines;
  `test_greenfield_semantic_quality_terms.py`: 72 lines). Proof: syntax proof
  passed for the touched modules and test; focused semantic-quality proof passed
  (`1 passed in 0.03s`); wider greenfield artifact proof passed (`157 passed
  in 195.20s`); and confirmed-create performance proof passed (`1 passed in
  9.61s`), preserving the under-30s create gate.
- 2026-06-04 confirmed-intent semantic term-index follow-through kept
  `greenfield_confirmed_text.semantic_terms` as the accepted-intent semantic
  API while moving its reusable token indexing onto
  `greenfield_domain_term_index.ordered_terms`. The shared term index now
  supports caller-owned `stem_ing_minimum_length`, so confirmed-intent overlap
  checks can preserve their previous gerund threshold without changing Atlas,
  Tribunal, semantic-model, risk, or release-scope callers. `greenfield_confirmed_text.py`
  no longer imports `normalize_domain_token` or loops over regex tokens for
  semantic terms locally. Touched files remain below limits
  (`greenfield_domain_term_index.py`: 90 lines;
  `greenfield_confirmed_text.py`: 399 lines;
  `test_greenfield_confirmed_text.py`: 84 lines). Proof: syntax proof passed
  for the touched modules and test; focused confirmed-text proof passed
  (`2 passed in 0.03s`); focused confirmed-intent proof passed
  (`30 passed in 35.33s`); wider artifact/proposal/post-confirm proof passed
  (`141 passed in 200.44s`); and confirmed-create performance proof passed
  (`1 passed in 9.63s`), preserving the under-30s create gate.
- 2026-06-04 Registry component term-index follow-through moved component
  phrase identity terms and contract-field transition candidates onto
  `greenfield_domain_term_index.ordered_terms`. `greenfield_component_terms.py`
  now owns only artifact-carrier stopword policy, `greenfield_component_contract_fields.py`
  owns only state/transition decisions, and `greenfield_component_semantic_contract.py`
  imports the phrase-identity owner directly instead of keeping a pass-through
  wrapper. The touched Registry component path no longer imports
  `normalize_domain_token` or loops over regex tokens locally for those term
  sets. Touched files remain below limits (`greenfield_component_terms.py`: 781
  lines; `greenfield_component_contract_fields.py`: 443 lines;
  `greenfield_component_semantic_contract.py`: 620 lines;
  `test_greenfield_component_spec_quality.py`: 440 lines). Proof: syntax proof
  passed for the touched modules and test; focused component-spec proof passed
  (`12 passed in 0.21s`); wider artifact/proposal proof passed
  (`120 passed in 162.97s`); and confirmed-create performance proof passed
  (`1 passed in 9.72s`), preserving the under-30s create gate.
- 2026-06-04 public quality-gate term-index follow-through moved prompt echo
  and semantic contract noun extraction in `greenfield_quality_gate.py` onto
  `greenfield_domain_term_index.ordered_terms`. The shared index now supports
  caller-owned `preserve_terms`, so the public quality gate can retain short
  domain abbreviations such as AI, ML, UI, and UX without owning a local regex
  token loop or direct `normalize_domain_token` import. Touched files remain
  below limits (`greenfield_domain_term_index.py`: 103 lines;
  `greenfield_quality_gate.py`: 659 lines;
  `test_greenfield_domain_profile_quality.py`: 275 lines). Proof: syntax proof
  passed for the touched modules and test; focused quality-gate proof passed
  (`17 passed in 13.90s`); wider greenfield proof passed (`168 passed in
  226.89s`); and confirmed-create performance proof passed (`1 passed in
  9.44s`), preserving the under-30s create gate.
- 2026-06-04 first-path actor term-index follow-through moved actor signature
  term extraction in `greenfield_first_path_clauses.py` onto
  `greenfield_domain_term_index.ordered_terms`. The first-path clause owner now
  keeps only action/capability/result grammar and actor-specific stopword policy,
  while the shared index preserves short domain actor terms such as AI, ML, UI,
  and UX. This prevents later plain-actor follow-up actions from bleeding into a
  qualified actor's first path after a visible result. Touched files remain below
  limits (`greenfield_first_path_clauses.py`: 742 lines;
  `test_greenfield_post_confirm_slop_regressions.py`: 674 lines). Proof:
  syntax proof passed for the touched module and test; focused post-confirm slop
  proof passed (`14 passed in 2.78s`); wider greenfield proof passed (`151
  passed in 237.66s`); and confirmed-create performance proof passed (`1 passed
  in 11.47s`), preserving the under-30s create gate.
- 2026-06-04 confirmed component label term-index follow-through moved
  `domain_label` token extraction in `greenfield_confirmed_components.py` onto
  `greenfield_domain_term_index.label_terms`. The shared term-index owner now
  separates visible label words from semantic normalized terms, preserving
  acronyms and alphanumeric labels such as AI, CRM, GIS, UI, UX, `3D`, and
  `W-2` while removing the component generator's local regex token loop.
  Touched files remain below limits (`greenfield_domain_term_index.py`: 131
  lines; `greenfield_confirmed_components.py`: 577 lines;
  `test_greenfield_component_spec_quality.py`: 455 lines). Proof: syntax proof
  passed for the touched modules and test; focused component-spec proof passed
  (`12 passed in 0.25s`); wider greenfield proof passed (`151 passed in
  233.14s`); and confirmed-create performance proof passed (`1 passed in
  11.90s`), preserving the under-30s create gate.
- 2026-06-04 component handoff title-match term-index follow-through moved
  generated component handoff workstream-title matching in `greenfield_experience.py`
  onto `greenfield_domain_term_index.ordered_terms`. The handoff owner now keeps
  only matching policy and stopwords, while the shared index handles plural
  folding so `status dashboards` can match `Status Dashboard Surface` and
  `reviews service` does not leak past the intended `review` and `service`
  stopwords. Touched files remain below limits (`greenfield_experience.py`: 481
  lines; `test_greenfield_experience_terms.py`: 55 lines). Proof: syntax proof
  passed for the touched module and test; focused experience/row proof passed
  (`2 passed in 0.08s`); wider greenfield proof passed (`152 passed in
  229.35s`); and confirmed-create performance proof passed (`1 passed in
  11.57s`), preserving the under-30s create gate.
- 2026-06-04 traceability semantic token term-index follow-through moved
  generated Radar, Registry, and Atlas traceability matching in
  `greenfield_traceability.py` onto `greenfield_domain_term_index.ordered_terms`.
  The traceability owner now keeps scoring thresholds and compound identifier
  expansion, while the shared index handles plural folding so component labels
  such as `Status Windows` can link to singular workstream titles such as
  `Build window proof`. Touched files remain below limits
  (`greenfield_traceability.py`: 661 lines; `test_greenfield_traceability_terms.py`:
  65 lines). Proof: syntax proof passed for the touched module and test;
  focused traceability/artifact proof passed (`41 passed in 162.78s`); wider
  greenfield proof passed (`153 passed in 230.09s`); and confirmed-create
  performance proof passed (`1 passed in 11.77s`), preserving the under-30s
  create gate.
- 2026-06-04 confirmed Radar backlog term-index follow-through moved
  `semantic_words` and `shares_product_terms` in
  `greenfield_confirmed_backlog_text_model.py` onto
  `greenfield_domain_term_index.ordered_terms`. The Radar backlog text model now
  keeps backlog-specific stopwords and first-slice text decisions, while the
  shared index handles plural folding so `status windows` and `window proof`
  share the same product terms without matching on generic release/path glue.
  Touched files remain below limits (`greenfield_confirmed_backlog_text_model.py`:
  473 lines; `test_greenfield_confirmed_backlog_terms.py`: 39 lines). Proof:
  syntax proof passed for the touched module and test; focused backlog text proof
  passed (`11 passed in 13.37s`); wider greenfield proof passed (`154 passed in
  228.69s`); and confirmed-create performance proof passed (`1 passed in
  12.05s`), preserving the under-30s create gate.
- 2026-06-04 Registry fallback term-window follow-through moved component label
  compounds and nearby context-window parsing from
  `greenfield_component_contract_differentiation.py` into
  `greenfield_component_term_windows.py`. Contract differentiation now keeps
  fallback-axis scoring and repair policy, while the term-window owner handles
  token parsing, plural folding, and short label compounds such as AI CRM without
  growing the near-limit `greenfield_component_terms.py` module. Touched files
  remain below limits (`greenfield_component_terms.py`: 781 lines;
  `greenfield_component_term_windows.py`: 75 lines;
  `greenfield_component_contract_differentiation.py`: 705 lines;
  `test_greenfield_component_spec_quality.py`: 481 lines). Proof: syntax proof
  passed for the touched modules and test; focused component-spec proof passed
  (`12 passed in 0.25s`); wider greenfield proof passed (`154 passed in
  224.99s`); and confirmed-create performance proof passed (`1 passed in
  11.72s`), preserving the under-30s create gate.
- 2026-06-04 Registry literal label-term follow-through moved component label
  term extraction from `greenfield_component_contract.py` and
  `greenfield_component_contract_fields.py` into
  `greenfield_component_term_windows.py`. Base contracts, semantic contracts,
  and fallback differentiation now share the same label-term owner, preserving
  short labels such as AI CRM and plural artifact-carrier phrases such as
  `policy guardrails` without reopening caller-local regex token loops. Touched
  files remain below limits (`greenfield_component_term_windows.py`: 91 lines;
  `greenfield_component_contract.py`: 554 lines;
  `greenfield_component_contract_fields.py`: 413 lines;
  `greenfield_component_semantic_contract.py`: 620 lines;
  `test_greenfield_component_spec_quality.py`: 505 lines). Proof: syntax proof
  passed for the touched modules and test; focused component/guardrail proof
  passed (`13 passed in 3.38s`); wider greenfield proof passed (`154 passed in
  216.42s`); and confirmed-create performance proof passed (`1 passed in
  10.18s`), preserving the under-30s create gate.
- 2026-06-04 Registry actor/action artifact-term follow-through moved
  actor-role token detection into `greenfield_actor_terms.py` and made
  `greenfield_component_terms.py` use cached action-form lookup when cleaning
  generated Registry artifact phrases. Component semantic context now imports
  the same actor-role classifier instead of carrying its own local role list,
  so phrases such as `inspector reviews permit note` become `permit note`
  consistently across base artifact cleanup and context extraction. Touched
  files remain below limits (`greenfield_actor_terms.py`: 61 lines;
  `greenfield_component_terms.py`: 776 lines;
  `greenfield_component_semantic_context.py`: 282 lines;
  `test_greenfield_component_spec_quality.py`: 519 lines;
  `test_greenfield_component_semantic_contract_quality.py`: 69 lines). Proof:
  syntax proof passed for the touched modules and tests; focused component
  proof passed (`14 passed in 0.14s`); wider greenfield artifact proof passed
  (`156 passed in 195.31s`); and confirmed-create performance proof passed
  (`1 passed in 9.29s`), preserving the under-30s create gate.
- 2026-06-04 Registry generic actor-label prefix follow-through moved
  local operator/reviewer prefix detection into `greenfield_actor_terms.py`.
  Component contract fields, contract differentiation, and rendered-spec
  quality now share `generic_actor_label_prefix`,
  `starts_with_generic_actor_label`, and `localize_generic_actor_label`
  instead of carrying local actor-prefix regexes. Generic prefixes that leave a
  concrete artifact behind, such as `Primary user request status` and
  `Risk reviewer guardrails`, now reduce to the owned artifact phrase, while
  bare generic actor labels such as `Operator approval packet` stay localized.
  Touched files remain below limits (`greenfield_actor_terms.py`: 107 lines;
  `greenfield_component_contract_fields.py`: 413 lines;
  `greenfield_component_contract_differentiation.py`: 700 lines;
  `greenfield_component_contract_quality.py`: 537 lines;
  `test_greenfield_component_spec_quality.py`: 560 lines). Proof: syntax proof
  passed for the touched modules and test; focused component proof passed
  (`14 passed in 0.17s`); wider greenfield artifact proof passed (`156 passed
  in 194.91s`); and confirmed-create performance proof passed (`1 passed in
  9.55s`), preserving the under-30s create gate.

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
