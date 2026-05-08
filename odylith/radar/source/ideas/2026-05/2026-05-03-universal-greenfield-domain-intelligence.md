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
Add a host-reasoned Domain Intelligence contract that turns vague greenfield intent into concrete backlog, program waves, provisional release plan, planned Registry components, host-authored Atlas topology, assumptions, risks, and validation obligations while keeping observed source, user intent, and Odylith assumptions distinct.

## Proposed Solution
Create a first-class `runtime/domain_intelligence` package that makes Odylith the evidence/schema/validation/apply layer, not the project-authoring brain. `odylith greenfield propose` performs a shallow repo evidence scan and emits a host-agnostic reasoning contract. The active supported host then uses its full reasoning capability to draft the concrete backlog, components, Atlas Mermaid sources, waves, release plan, assumptions, risks, validation strategy, and open questions in normal chat. `odylith greenfield apply` validates the accepted proposal, runs a deterministic greenfield Tribunal, requires host-authored `mermaid_source` for each Atlas draft, rejects disconnected or duplicated topology, writes only through owned Radar, Registry, Atlas, release-targeting, and Compass memory paths after `--confirm`, and performs one final Radar/Registry/Atlas/Compass refresh after all accepted artifacts exist.

## Research Signals
External ecosystem checks argue against a small in-code taxonomy as the proposal author. GitHub Octoverse 2025 shows high-volume new repository creation, AI/agent growth, TypeScript-heavy application work, Python/Jupyter AI and data-science work, and private/product repos growing alongside public open source. CNCF organizes cloud-native work around infrastructure, delivery, observability, security, AI/ML, and runtime ecosystems. Apache describes mature open-source projects across data, cloud, search, libraries, geospatial, IoT, and related categories. NASA's software and open-data surfaces show science projects built from code, data, analysis pipelines, simulation/modeling tools, visualization, reproducibility, and sustained scientific libraries. Those signals prove greenfield intent is open-world; v0.1.14 therefore keeps host reasoning responsible for the project-specific plan while Odylith runtime validation owns evidence tiers, confirmation gates, topology hygiene, release targeting, program/wave formation, and durable memory.

## Scope
- Add `odylith greenfield propose` and `odylith greenfield apply`.
- Keep host adapters thin; every supported host routes to the same CLI/runtime path.
- Let the host model reason over any product, science, math, research,
  infrastructure, art, education, policy, device, data, or mixed project shape;
  do not constrain the proposal to an in-code domain list.
- Require the host-authored proposal to carry concrete backlog candidates,
  candidate Registry components, host-authored Atlas Mermaid sources,
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
Greenfield propose returns a low-latency, provider_calls=0 host-reasoning contract for any vague or precise greenfield prompt.
The host-authored proposal includes backlog candidates, program waves, release plan, planned Registry components, draft Atlas Mermaid sources, assumptions, risks, validation strategy, open questions, and exact apply commands.
Provider-free greenfield scaffolds include a multi-view Atlas suite with mutually traceable workstream/component links; the robot-swarm logistics path emits conflict, safety, telemetry, deployment-boundary, and observability/audit views in addition to baseline topology.
Greenfield proposals carry a project-first brief before backlog: direction options, pre-coding checkpoints, coding-readiness gates, and host-independent commands must be visible in text and JSON before apply.
Greenfield Registry component specs stay component-owned: they must not copy project-level risk/security/compliance posture into every dossier, and each spec must name the component's own boundary, outside-boundary exclusions, collaborators, interfaces, failure modes, proof obligations, first source path, most specific child workstream anchor, and component-local diagram set instead of project-wide topology links.
Greenfield apply writes through owned Radar, Registry, Atlas, release-targeting, and Compass memory paths only after --confirm, preserving user_intent evidence and source-backed truth separation.
Apply rejects missing Mermaid source, duplicated diagram source, incomplete proposal sections, and invalid evidence tiers before any governed write.
Apply/create closeout leads with the project workstream and readiness gates, then names the eventual first coding workstream as a later lane rather than the immediate next action.
Host prompt routing avoids noisy raw Observation chatter for normal greenfield intents while preserving earned intervention paths.
Greenfield apply runs a deterministic proposal Tribunal before any governed write and refreshes Radar, Registry, Atlas, and Compass once after all accepted artifacts are written.
Compass timeline audit filters zero-file prompt-intervention narration so routing notes do not render as fake implementation history.

## Validation
- Unit tests for the host-reasoning request contract, open-world proposal validation, required host-authored Mermaid sources, duplicate-topology rejection, program waves, release plan, CLI JSON, host greenfield routing, component authoring user-intent metadata, and Compass zero-file intervention chatter filtering.
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
  scaffold now emits five architecture views and the robot-swarm logistics
  profile emits ten domain-specific views while validation and Tribunal still
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
  legacy normalization, validation rejection, robot-swarm customization options,
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
  to Radar/Atlas and kept Registry dossiers component-local: DeFi generated
  specs now bind Risk Console to `B-002` and `D-002,D-003`, Risk Signal Engine
  to `B-003` and `D-002,D-003,D-004`, Scenario Replay Harness to `B-004` and
  `D-005`; host-authored components without component-level diagram refs no
  longer inherit system-context/program-wave diagrams. Proof:
  `python3 -m pytest tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_component_authoring.py
  tests/unit/runtime/test_governed_artifact_tribunal.py -q` (`39 passed`).
- 2026-05-08 project-first UX deepening made proposal text render a fuller
  project intelligence board before backlog, including all control-surface
  rows, complete customization flow through the no-code-until-plan step, deeper
  per-layer project reality, project design board rows, host-independent
  "customize by saying" examples, and apply/create closeouts that label the
  child workstream as a future implementation lane after gates instead of an
  immediate coding instruction. Proof: `python3 -m pytest
  tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_greenfield_intelligence_schema.py
  tests/unit/runtime/test_component_authoring.py
  tests/unit/install/test_local_release_smoke.py -q` (`58 passed`);
  `python3 -m py_compile` passed for the touched greenfield UX modules and
  release smoke script.
- 2026-05-08 traceability writer hardening fixed the remaining applied-Radar
  sludge discovered by fresh DeFi temp-repo proof: structured risks,
  questions, dependencies, and release stages now render as complete governed
  bullets instead of fragments like `R1.`, `Q1.`, `domain contract.`, or
  `command.`; question punctuation is preserved; DeFi customization prompts no
  longer split into lowercase fragments. Proof: source-local `greenfield
  propose` produced 270-line project-first text with 24 project-intelligence
  layers, source-local apply wrote all four DeFi Radar workstreams with no
  shallow-fragment hits, `python3 -m pytest
  tests/unit/runtime/test_greenfield_proposals.py
  tests/unit/runtime/test_greenfield_intelligence_schema.py
  tests/unit/runtime/test_component_authoring.py
  tests/unit/install/test_local_release_smoke.py -q` passed (`58 passed`), and
  `python3 -m py_compile` passed for the touched greenfield modules.
- Deepening pass split science/math into targeted subdomains and added fixture
  proof for commerce, SaaS, dashboards, AI assistants, data ingestion, CLI
  libraries, physics simulation, differential-equation solvers, computational
  biology pipelines, formal proof libraries, statistics/econometrics notebooks,
  math education, geospatial climate analysis, ML experiment platforms, and
  robotics calibration workflows. Formal-proof proposals now carry proof
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
- New CLI family: `odylith greenfield apply`.
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
  `migration-observer:0.1.15:browser-surfaces:7d4664249c0d`.
  These markers cover the deepened greenfield skill guidance, refreshed
  Domain Intelligence Atlas/Registry/Radar browser surfaces, updated managed
  security-and-trust guidance, updated public README/operator/release-note/security
  guidance, the v0.1.15 Compass/Radar/Registry/Casebook browser-surface refresh
  from the deeper greenfield diagram-suite contract, the project-first
  direction-option/readiness-gate guidance refresh, the engine-integrity
  validator and expanded capability inventory, the canonical project-intelligence
  proposal object and parent Radar persistence, explicit project/workstream
  invalidation rules, first-class workstream scope and owners, component-local
  Registry dossier topology, and bundled install-managed dashboard copies.
  Existing consumer governance truth remains unchanged; upgrades
  refresh managed guidance/assets and keep proposal writes explicit through
  `odylith greenfield apply --confirm`.

## Test Strategy
- Run focused unit tests for domain intelligence, host routing, component authoring, CLI dispatch, show capabilities, and Compass transaction filtering.
- Run governance validators for Casebook, backlog, plan binding/traceability as touched, release migration gate, and refreshed Radar/Registry/Atlas/Compass surfaces.
- Run headless browser smoke over the regenerated dashboards so the new records and the timeline-audit fix are visible without layout regressions.

## Open Questions
- Should a future signed domain-pack marketplace augment host reasoning with
  curated evidence, examples, and validators after v0.1.14 ships the open-world
  host-reasoned baseline?
