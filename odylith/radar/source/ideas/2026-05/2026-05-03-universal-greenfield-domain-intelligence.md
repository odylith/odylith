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

ordering_rationale: Operator-facing greenfield UX failure blocked a core consumer-lane onboarding path and belongs in the v0.1.13 release target alongside cross-host latency and intervention integrity.

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
Add a provider-free domain-intelligence compiler that converts vague greenfield intent into concrete backlog, program waves, provisional release plan, planned Registry components, draft Atlas topology, assumptions, risks, and validation obligations while keeping observed source, user intent, and Odylith assumptions distinct.

## Proposed Solution
Create a first-class `runtime/domain_intelligence` package with a provider-free archetype catalog and a greenfield proposal compiler. The compiler reads shallow repo posture, classifies user-stated project intent, and returns backlog candidates, program waves, a provisional release plan, planned Registry components, draft Atlas diagrams, assumptions, risks, validation obligations, open questions, and exact confirmation-gated apply commands. The apply path writes only through owned Radar, Registry, Atlas, and release-targeting authoring paths after `--confirm`.

## Research Signals
External ecosystem checks support the first-class archetype set instead of a narrow ecommerce-only fix. GitHub Octoverse 2025 shows high-volume new repository creation, AI/agent growth, TypeScript-heavy application work, Python/Jupyter AI and data-science work, and private/product repos growing alongside public open source. CNCF organizes cloud-native work around infrastructure, delivery, observability, security, AI/ML, and runtime ecosystems. Apache describes mature open-source projects across data, cloud, search, libraries, geospatial, IoT, and related categories. NASA's software and open-data surfaces show science projects built from code, data, analysis pipelines, simulation/modeling tools, visualization, reproducibility, and sustained scientific libraries. The v0.1.13 catalog therefore covers product apps, SaaS, commerce, cloud/infra, AI agents, data platforms, CLI/libraries, security/compliance, IoT/instrumentation, mobile/game/education, and science/math with validation-specific obligations. The follow-on hardening pass added explicit fit explainability and alternate archetype candidates so ambiguous prompts can be corrected without losing the low-latency provider-free path.

## Scope
- Add `odylith greenfield propose` and `odylith greenfield apply`.
- Keep host adapters thin; Claude, Codex, and future hosts route to the same CLI/runtime path.
- Cover commerce, SaaS, cloud/infra, data, AI agent, CLI/library, security/compliance, IoT/instrumentation, mobile/game/education, and general app archetypes.
- Treat science/math as a first-class family with separate formal-proof,
  computational-notebook, numerical-simulation, scientific-pipeline,
  geospatial/environmental, ML-experiment, and math-education proposal lenses.
- Include deterministic primary/alternate fit classification, acronym-safe
  project titles, domain-specific first-slice validation wording, parent/child
  program formation, wave-to-workstream policy, and provisional release strategy.
- Preserve evidence separation: observed source, user intent, and Odylith assumptions must stay distinct.
- Keep proposal generation provider-free by default and write only after explicit confirmation.
- Filter Compass timeline audit entries so zero-file prompt-intervention narration does not become fake implementation history.

## Non-Goals
- Do not add provider-backed enrichment in v0.1.13.
- Do not let host-specific Claude or Codex hooks own the proposal logic.
- Do not turn greenfield assumptions into source-backed governance claims.

## Risks
- Broad prompts can sound authoritative even when source evidence is empty; every generated detail must carry user-intent or Odylith-assumption evidence.
- Domain archetypes can drift into templates if they stop producing domain-specific validation and topology obligations.
- Generic science/math routing can produce harmful advice if proof projects,
  notebook/statistical analysis, numerical solvers, ML experiments, and
  geospatial workflows share one validation script.
- Apply-time writes can pollute consumer repos unless they stay confirmation-gated and route through owned Radar, Registry, Atlas, and release authoring paths.

## Dependencies
- Depends on B-141 for the v0.1.13 host/runtime integrity lane: greenfield prompt routing must preserve low-latency host behavior, Intervention Engine separation, and consumer-lane feature integrity.

## Success Metrics
Greenfield propose returns deterministic provider_calls=0 output for commerce, SaaS, cloud, data, AI agent, CLI/library, science/math, security/compliance, IoT/instrument, mobile/game/education, and general app prompts.
Proposal output includes backlog candidates, program waves, release plan, planned Registry components, draft Atlas diagrams, assumptions, risks, validation strategy, open questions, and exact apply commands.
Greenfield apply writes through owned Radar, Registry, Atlas, and release-targeting paths only after --confirm, preserving user_intent evidence and source-backed truth separation.
Host prompt routing avoids noisy raw Observation chatter for normal greenfield intents while preserving earned intervention paths.
Compass timeline audit filters zero-file prompt-intervention narration so routing notes do not render as fake implementation history.

## Validation
- Unit tests for deterministic greenfield proposals, domain classification, science/math validation obligations, program waves, release plan, provider-free CLI JSON, host greenfield routing, component authoring user-intent metadata, and Compass zero-file intervention chatter filtering.
- CLI proof for `odylith greenfield propose --format json` on empty/thin repo posture.
- Governance proof through Casebook, Radar, Registry, Atlas, and Compass refreshes.
- Browser proof for refreshed Radar, Registry, Atlas, Casebook, and Compass surfaces after generated assets update.

## Validation Evidence
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_greenfield_host_routing.py tests/unit/runtime/test_component_authoring.py tests/unit/runtime/test_compass_transaction_runtime.py tests/unit/runtime/test_show_capabilities.py tests/unit/test_cli.py` passed with 200 tests.
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_agents.py tests/unit/install/test_codex_project_assets.py tests/unit/install/test_claude_effective_settings.py tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_casebook_source_validation.py tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_validate_guidance_behavior.py tests/unit/runtime/test_validate_discipline.py tests/unit/install/test_migration_runtime.py tests/unit/install/test_casebook_metadata_migration.py tests/integration/install/test_lifecycle_simulator.py tests/integration/runtime/test_governance_sync_performance.py` passed with 269 tests.
- Full browser proof passed with 185 tests and 1 skipped case across Atlas, Casebook, Compass, Radar, Registry, intervention visibility, filter audit, onboarding, and regression surfaces.
- Fresh consumer proof installed the shipped runtime, executed source v0.1.13 `greenfield propose/apply`, and confirmed provider-free commerce output plus 4 backlog records, 5 planned components, 2 draft diagrams, and a bootstrapped `next` release selector after explicit confirmation.
- Governance proof refreshed Casebook, Radar, Registry, Atlas, and Compass; `casebook validate`, `backlog-contract`, `plan-workstream-binding`, `plan-risk-mitigation`, `release migration-gate --target-version 0.1.13`, and `git diff --check` passed.
- Engine-integrity follow-up proved the Domain Intelligence capability map,
  markup-safe repo identity extraction, host routing, and science/math
  greenfield proposal path through the 568-test engine suite, the 208-test
  host/migration suite, and the 185-test browser matrix without provider calls
  or consumer-lane source claims.
- Deepening pass split science/math into targeted subdomains and added fixture
  proof for commerce, SaaS, dashboards, AI assistants, data ingestion, CLI
  libraries, physics simulation, differential-equation solvers, computational
  biology pipelines, formal proof libraries, statistics/econometrics notebooks,
  math education, geospatial climate analysis, ML experiment platforms, and
  robotics calibration workflows. Formal-proof proposals now carry proof
  checker/theorem obligations and explicitly avoid numerical tolerance/random
  seed advice.
- Follow-on hardening added deterministic alternate-fit classification,
  acronym-safe titles, a dedicated proposal-rendering owner, program-formation
  output, and domain-specific first-slice validation text so broad prompts do
  not fall back to generic proof-harness wording.
- Follow-on proof passed `27` focused greenfield tests, `219` focused
  greenfield/host/CLI tests, `148` bundle/hygiene/governance tests, the `586`
  test engine/host-parity matrix, the `208` test install/migration lifecycle
  matrix, and the `185 passed, 1 skipped` browser matrix. The release migration
  gate reported `ok: true`, `blocked: 0`, and `ungated: 0`.

## Rollout
- Ship in v0.1.13 with B-141 because the user-facing failure is inseparable from consumer-lane host UX hardening: low latency is not enough if empty-repo greenfield prompts dead-end.
- Keep proposal generation enabled by default and provider-free; reserve future provider-backed enrichment for an explicit follow-up mode.
- Prove empty/thin consumer UX through CLI, host-routing tests, migration-gate coverage, and browser-surface refreshes before release.

## Why Now
The greenfield failure was reported during the v0.1.13 consumer-lane hardening pass. Fixing latency while still refusing broad new-project intent would preserve speed but regress the product purpose.

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
- New CLI family: `odylith greenfield apply`.
- `odylith show` empty/thin scenarios now point to proposal-first greenfield governance instead of only asking the operator to provide all fields.
- Component registration can record planned consumer components with `user_intent` evidence without claiming source-backed ownership.

## Migration/Compatibility
- Existing consumer repos need no data migration. Upgrading to v0.1.13 installs the new CLI/runtime path, managed guidance, and host skill shims. Existing source-backed governance remains unchanged; greenfield proposals are additive and confirmation-gated.
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
  `migration-observer:0.1.13:install-managed-assets:20dacaa00761`,
  `migration-observer:0.1.13:browser-surfaces:7a832cdde5ae`,
  `migration-observer:0.1.13:browser-surfaces:e7074b845e26`.
  These markers cover the deepened greenfield skill guidance, refreshed
  Domain Intelligence Atlas/Registry/Radar browser surfaces, and bundled
  install-managed dashboard copies. Existing consumer governance truth remains
  unchanged; upgrades refresh managed guidance/assets and keep proposal writes
  explicit through `odylith greenfield apply --confirm`.

## Test Strategy
- Run focused unit tests for domain intelligence, host routing, component authoring, CLI dispatch, show capabilities, and Compass transaction filtering.
- Run governance validators for Casebook, backlog, plan binding/traceability as touched, release migration gate, and refreshed Radar/Registry/Atlas/Compass surfaces.
- Run headless browser smoke over the regenerated dashboards so the new records and the timeline-audit fix are visible without layout regressions.

## Open Questions
- Should optional provider-backed enrichment become a later explicit mode after the provider-free v0.1.13 baseline ships?
