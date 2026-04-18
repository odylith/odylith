Status: In progress
Created: 2026-04-17
Updated: 2026-04-18
Backlog: B-110, B-111, B-112, B-113, B-114, B-115, B-116, B-117

# Adaptive Agent Operating Character, Credit-Safe And Benchmark-Proved

## Goal
Make Agent Operating Character the v0.1.11 platform layer that changes how an
agent behaves under pressure without becoming a rigid posture router or burning
hidden host-model credits.

The runtime loop is:

`intent -> local pressure observations -> adaptive stance -> hard-law checks -> ranked affordances -> admissible action -> proof -> compact learning -> benchmark evidence -> updated priors`

## Decisions
- B-110 is the release-bound umbrella for this effort; B-111 through B-117 are its execution-wave children.
- Named postures such as Scout, Steward, Verifier, Foreman, Witness, Tribunal, and Operator are UX vocabulary and benchmark labels, not a runtime state machine.
- Deterministic hard laws remain fail-closed: CLI-first governed truth, proof-backed completion claims, visible-intervention proof, queue non-adoption, bounded delegation, public benchmark proof, consumer-lane mutation guard, and explicit model-consuming commands only.
- Adaptive character is represented as a stance vector across attention, restraint, agency, honesty, coordination, memory, judgment, voice, and accountability.
- Pressure is open-world. Known archetypes seed tests and benchmarks, while novel pressure is represented through features such as ambiguity, proof risk, governed-truth risk, delegation risk, visibility risk, recurrence, lane-boundary risk, urgency, uncertainty, and credit risk.
- Voice and intervention rendering must stay live and evidence-shaped. Character
  may emit a recovery affordance, evidence, visibility proof requirement, and
  owner surface, but it must not emit canned Observation/Proposal copy or turn
  named postures into a runtime state machine.
- Unsupported host families or execution lanes are fail-closed hard-law inputs, not advisory metadata. Character may normalize known aliases, but an unknown host or lane must defer to a supported Codex/Claude and dev/dogfood/consumer contract before admitting work.
- Learning is benchmark-gated. Session memory may nudge the current turn, but durable practice requires deterministic validation, benchmark evidence, or Tribunal doctrine.
- Hot character checks are Tier 0/Tier 1 local computation only: no provider calls, no host model calls, no subagent spawn for classification, no broad scan, no projection-store expansion, no full validation, and no benchmark execution.
- Hard-law semantics now have one shared policy source for recovery actions,
  recovery cues, visible-intervention eligibility, and block/defer decisions.
  Pressure extraction and law applicability use the same signal kernel so the
  runtime does not drift into duplicated regex policy.
- Benchmark sovereignty is a public-claim law, not a generic "benchmark word"
  blocker. Learning-from-benchmark and benchmark-feedback intents remain
  admissible local work; README, release-note, publish, shipped/proven, or
  explicit public-claim intents still require benchmark proof.
- Guidance Behavior and Agent Operating Character benchmark scenarios are
  explicitly tagged to B-110 so program/release proof, Context/Execution
  adoption metrics, and family-level benchmark status carry the same governed
  workstream anchor instead of reporting unnecessary widening.
- Character signal extraction distinguishes unsafe moves from operator
  instructions to prevent those moves. Negated delegation, queue adoption, and
  model-credit phrases are admissible discipline work; actual broad
  delegation, queue adoption, and model-credit spend remain hard-law pressure.
- CLI-first hard law applies where a CLI writer exists or the target is a
  known CLI-owned surface. Allowed authored governance surfaces, including the
  technical plan, must not false-block without CLI-writer evidence.
- Release proof execution is admissible proof-gathering work. Publishing or
  writing public shipped/proven claims remains blocked until benchmark proof is
  present.

## Related Records
- Umbrella: B-110.
- Child waves: B-111, B-112, B-113, B-114, B-115, B-116, B-117.
- Related execution and context work: B-099, B-100, B-101, B-102, B-103, B-104.
- Related visible intervention work: B-096, B-105, B-106, B-107, B-108, B-109.
- Related learning and governance cases: CB-104, CB-121, CB-122, CB-123 where applicable.
- Related bug search: no stronger existing Casebook bug was found for the adaptive character layer itself before this plan was created.

## Contracts
- `odylith_agent_operating_character.v1`
- `odylith_agent_operating_character_learning.v1`
- `odylith_agent_operating_character_runtime_budget.v1`
- `odylith_agent_operating_character_host_lane_support.v1`
- `agent_operating_character_evaluation_corpus.v1`
- `odylith_agent_operating_character_validation.v1`
- Compact practice events under `odylith_agent_operating_character_learning.v1`
  now carry the required learning-spine fields: event id, timestamp placeholder,
  host/lane, pressure features, stance vector, hard-law results, decision,
  recovery action, proof obligation, proof status, outcome, intervention
  visibility, zero-credit counters, benchmark family/case ids, Tribunal
  candidate state, source refs, fingerprint, and retention class.

## Implementation Waves
- B-111 Governance Alignment: update Radar, release targeting, execution program, Registry specs, Atlas topology, AGENTS/guidelines, skills, and Compass.
- B-112 Runtime And Budget Kernel: add `src/odylith/runtime/character/`, hard laws, pressure observations, stance vectors, ranked affordances, and credit/latency budget enforcement.
- B-113 Learning Spine: add compact learning events, retention classes, recurrence fingerprints, noise suppression, and benchmark/Tribunal promotion hooks.
- B-114 Subsystem Integration: connect Context, Execution, Proof State, Router/Orchestrator, Memory, Intervention, Chatter, Tribunal, and surfaces through compact summaries and contracts.
- B-115 Tooling And Host Parity: add `odylith character status/check/explain`, shared skill, Codex shim, Claude shim, and lane parity.
- B-116 Benchmark Sovereignty: add `agent_operating_character` benchmark family, adaptive replay cases, novelty/generalization cases, latency/credit metrics, and publication guards.
- B-117 Surfaces And Release Proof: refresh Radar, Compass, Registry, Atlas, Casebook, Dashboard, browser smoke tests, and full release proof after pinned dogfood is repaired.

## Interfaces
- `odylith character status --repo-root . [--json]`
- `odylith character check --repo-root . --intent-file PATH [--host HOST] [--lane dev|dogfood|consumer] [--json]`
- `odylith character explain --repo-root . --decision-id ID [--json]`
- `odylith validate agent-operating-character --repo-root . [--case-id ID...] [--json]`
- `odylith benchmark --profile quick --family agent_operating_character --no-write-report --json`

## Success Criteria
- The character validator is deterministic, credit-free, and green for seeded cases.
- Guidance Behavior remains green as the first deterministic pressure-family lane.
- The quick `agent_operating_character` benchmark family selects only that family and reports hard-law, stance, learning, latency, and credit metrics.
- Hot-path metrics prove provider calls, host model calls, broad scans, full validation, projection expansion, and benchmark execution are all zero.
- Durable learning events are compact, sanitized, fingerprinted, and not transcript-shaped.
- Codex and Claude expose the same character contract across dev, dogfood, and consumer lanes.
- Codex and Claude host model aliases normalize to adapter families; Character
  pressure classification, stance, hard laws, affordances, validation, and
  benchmark proof remain local and credit-free.
- Unknown hosts, unknown lanes, malformed benchmark assertions, unsupported
  learning outcomes, duplicate stringified evidence keys, missing intent files,
  and alias-heavy CLI inputs are covered by deterministic tests.
- `odylith character check` records a local `.odylith/cache` decision receipt,
  and `odylith character explain` explains that receipt without model calls,
  provider calls, validation, benchmark execution, broad scans, or projection
  expansion.
- Public claims remain blocked until full matched-pair proof passes.

## Validation Plan
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_agent_operating_character.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_validate_agent_operating_character.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_corpus.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py tests/unit/test_cli_audit.py`
- `./.odylith/bin/odylith validate guidance-behavior --repo-root .`
- `./.odylith/bin/odylith validate agent-operating-character --repo-root .`
- `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior --no-write-report --json`
- `./.odylith/bin/odylith benchmark --profile quick --family agent_operating_character --no-write-report --json`

## Validation Evidence
- `PYTHONPATH=src python -m py_compile src/odylith/runtime/character/*.py src/odylith/runtime/governance/validate_agent_operating_character.py src/odylith/cli.py`: passed.
- `python -m json.tool odylith/runtime/source/agent-operating-character-evaluation-corpus.v1.json`: passed.
- `python -m json.tool odylith/runtime/source/optimization-evaluation-corpus.v1.json`: passed.
- `PYTHONPATH=src python -m odylith.cli character status --repo-root . --json`: passed; reported Codex and Claude across dev, dogfood, and consumer lanes, with `provider_calls=0`, `host_model_calls=0`, `broad_scans=0`, `full_validations=0`, and `projection_expansions=0`.
- `PYTHONPATH=src python -m odylith.cli validate agent-operating-character --repo-root . --json`: passed, 19 cases, 0 issues, 8 host/lane parity rows, `character_hard_law_pass_rate=1.0`, `character_hot_path_budget_pass_rate=1.0`, `character_provider_call_count=0`, `character_host_model_call_count=0`, `character_false_allow_rate=0.0`, `character_false_block_rate=0.0`.
- `PYTHONPATH=src python -m odylith.cli validate guidance-behavior --repo-root . --json`: passed, 6 cases, 11 checks, 0 errors.
- `PYTHONPATH=src python -m odylith.cli benchmark --repo-root . --profile quick --family agent_operating_character --no-write-report --json`: provisional pass, 7 selected scenarios including `character-host-lane-parity-matrix`, hard quality gate cleared, 0 hard-gate failures, fairness contract passed; advisory widening remains nonblocking mechanism attention for this diagnostic family.
- Superseded on 2026-04-18 by B-110-tagged benchmark scenarios: quick `agent_operating_character` now clears hard, secondary, and advisory checks with `odylith_requires_widening_rate=0.0`.
- `PYTHONPATH=src python -m odylith.cli benchmark --repo-root . --profile quick --family guidance_behavior --no-write-report --json`: provisional pass, 6 selected scenarios, 0 hard-gate failures, `odylith_on` validation success `1.0`, critical validation success `1.0`, critical path recall `1.0`.
- `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/test_cli.py tests/unit/test_cli_audit.py -k 'agent_operating_character or character'`: 26 passed, 263 deselected.
- `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/test_cli.py tests/unit/test_cli_audit.py tests/unit/runtime/test_execution_engine_handshake.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_odylith_benchmark_isolation.py tests/unit/install/test_codex_project_assets.py -k 'agent_operating_character or character or guidance_behavior or observed_paths or public_and_bundle or codex_project_assets'`: 40 passed, 263 deselected before host/lane parity hardening; superseded by the 26-test focused rerun above for new Character changes.
- `./.odylith/bin/odylith sync --repo-root . --impact-mode selective --proceed-with-overlap -- ...`: passed, including plan/workstream binding, backlog contract, Registry contract, Atlas refresh, Compass, Radar, Registry, Casebook, shell render, source bundle mirror, and Registry forensics.
- `./.odylith/bin/odylith atlas auto-update --repo-root . --all-stale --runtime-mode standalone`: passed; refreshed two unrelated stale review-only diagrams (`D-031`, `D-032`) and brought Atlas to 39 fresh / 0 stale.
- `./.odylith/bin/odylith atlas auto-update --repo-root . --all-stale --runtime-mode standalone`: passed again after the evidence-only Radar refresh; refreshed `D-001` and brought Atlas back to 39 fresh / 0 stale.
- `./.odylith/bin/odylith sync --repo-root . --check-only --impact-mode selective --proceed-with-overlap`: passed after Atlas stale review markers were refreshed; Registry, Radar, plan, Atlas, and delivery-intelligence checks are green.
- `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_context_execution_alignment_browser.py tests/integration/runtime/test_intervention_visibility_browser.py tests/integration/runtime/test_compass_browser_regression_matrix.py tests/integration/runtime/test_atlas_sort_browser.py tests/integration/runtime/test_casebook_sort_browser.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`: 158 passed, 1 skipped.
- `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_atlas_sort_browser.py`: 23 passed after the final Atlas D-001 refresh.
- `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_context_execution_alignment_browser.py`: 78 passed.
- `./.odylith/bin/odylith sync --repo-root . --impact-mode selective --proceed-with-overlap ...`: passed with plan/workstream binding, backlog contract, Registry contract, Atlas freshness, Compass, Radar, Registry, Casebook, shell render, source bundle mirror, and follow-up freshness refreshes.
- `./.odylith/bin/odylith sync --repo-root . --check-only --impact-mode selective --proceed-with-overlap`: passed, including Registry requirements, component registry contract, plan/workstream binding, backlog contract, plan risk/mitigation, Atlas freshness, and delivery-intelligence freshness.
- `PYTHONPATH=src python -m py_compile src/odylith/runtime/character/*.py src/odylith/runtime/governance/validate_agent_operating_character.py src/odylith/cli.py`: passed after the unsupported-host/lane and malformed-assertion hardening pass.
- `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/test_cli.py -k 'character or agent_operating_character'`: 25 passed, 118 deselected; covers unsupported host/lane deferral, duplicate stringified evidence keys, CLI alias normalization, missing intent files, malformed benchmark assertions, unknown learning outcomes, selected-case filtering, mirrors, and dispatch.
- `PYTHONPATH=src python -m odylith.cli validate agent-operating-character --repo-root . --json`: passed after hardening, 19 cases, 0 issues, `character_hard_law_pass_rate=1.0`, `character_hot_path_budget_pass_rate=1.0`, `character_provider_call_count=0`, `character_host_model_call_count=0`, `character_false_allow_rate=0.0`, and `character_false_block_rate=0.0`.
- `PYTHONPATH=src python -m odylith.cli validate guidance-behavior --repo-root .`: passed after hardening, 6 cases and 11 guidance checks.
- `PYTHONPATH=src python -m odylith.cli benchmark --repo-root . --profile quick --family agent_operating_character --no-write-report --json`: provisional pass after hardening, 7 selected scenarios, hard quality gate cleared, 0 hard-gate failures, fairness contract passed; advisory widening remains nonblocking mechanism attention.
- Superseded on 2026-04-18 by B-110-tagged benchmark scenarios: quick `agent_operating_character` now clears hard, secondary, and advisory checks with `odylith_requires_widening_rate=0.0`.
- `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_execution_engine.py tests/unit/runtime/test_execution_engine_handshake.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_tooling_context_routing.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_intervention_engine.py tests/unit/test_cli.py`: 431 passed.
- `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_atlas_sort_browser.py`: 23 passed after the latest code hardening.
- `PYTHONPATH=src pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_intervention_alignment_evidence.py`: 39 passed after the adaptive proof/voice/platform-integration hardening pass.
- `PYTHONPATH=src python -m py_compile src/odylith/runtime/character/*.py src/odylith/runtime/governance/validate_agent_operating_character.py src/odylith/runtime/intervention_engine/alignment_evidence.py src/odylith/runtime/execution_engine/runtime_surface_governance.py src/odylith/cli.py`: passed after the same hardening pass.
- `PYTHONPATH=src pytest -q tests/unit/runtime/test_execution_engine.py tests/unit/runtime/test_execution_engine_handshake.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_intervention_alignment_evidence.py tests/unit/test_cli.py tests/unit/test_cli_audit.py -k 'character or agent_operating_character or guidance_behavior or execution_engine or intervention or context_packet or memory'`: 141 passed, 427 deselected.
- `./.odylith/bin/odylith validate agent-operating-character --repo-root . --json`: passed after hardening, 19 cases, 0 issues, platform integration passed across Context, Execution, Memory, Intervention, and Benchmark; proof obligation, tool affordance, memory recurrence, learning replay, and intervention visibility metrics all reported `1.0`; hot-path host model and provider call counts stayed `0`.
- `./.odylith/bin/odylith validate guidance-behavior --repo-root .`: passed after hardening, 6 cases and 11 guidance checks.
- `./.odylith/bin/odylith benchmark --repo-root . --profile quick --family agent_operating_character --no-write-report --json`: provisional pass after hardening, 7 selected scenarios, hard quality gate cleared, fairness contract passed, 0 hard-gate failures; advisory widening-rate check remains nonblocking mechanism attention and is not release/public proof.
- Superseded on 2026-04-18 by B-110-tagged benchmark scenarios: quick `agent_operating_character` now clears hard, secondary, and advisory checks with `odylith_requires_widening_rate=0.0`.
- `./.odylith/bin/odylith benchmark --repo-root . --profile quick --family guidance_behavior --no-write-report --json`: provisional pass after hardening, 6 selected scenarios, hard quality gate cleared, fairness contract passed, 0 hard-gate failures, no advisory failures.
- `PYTHONPATH=src python -m py_compile src/odylith/runtime/character/*.py src/odylith/runtime/governance/validate_agent_operating_character.py src/odylith/cli.py`: passed after the learning-spine and `character explain` implementation.
- `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/test_cli.py -k 'character or agent_operating_character'`: 32 passed, 118 deselected; adds compact practice-event contract coverage, sanitized source-ref handling, local decision-record explain, unknown decision failure, status last-decision reporting, validator practice-event rejection, and top-level CLI dispatch coverage for status/explain.
- `PYTHONPATH=src python -m odylith.cli validate agent-operating-character --repo-root .`: passed after the practice-event validator became required.
- `PYTHONPATH=src python -m odylith.cli validate guidance-behavior --repo-root .`: passed after the practice-event integration.
- `PYTHONPATH=src python -m odylith.cli character status --repo-root . --json`: passed after status began reporting the runtime summary, active hard laws, learning outcomes/retention classes, benchmark-proof freshness posture, and last decision digest.
- `PYTHONPATH=src python -m odylith.cli character check --repo-root . --intent-file <tmp> --host claude-sonnet --lane pinned-dogfood --json`: passed; normalized to Claude/dogfood, blocked proofless completion, emitted `benchmark_pressure` practice event, and kept host model calls at 0.
- `PYTHONPATH=src python -m odylith.cli character explain --repo-root . --decision-id character:claude:dogfood:980a0af875f63e4a --json`: passed from the local decision receipt; returned `explained`, `block`, `fresh_proof_completion`, and host model calls 0.
- `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_execution_engine.py tests/unit/runtime/test_execution_engine_handshake.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_tooling_context_routing.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_isolation.py tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py tests/unit/install/test_codex_project_assets.py tests/unit/test_cli.py tests/unit/test_cli_audit.py`: 616 passed.
- `PYTHONPATH=src python -m odylith.cli benchmark --repo-root . --profile quick --family agent_operating_character --no-write-report --json`: provisional pass after the learning-spine/explain implementation; 7 selected scenarios, hard quality gate cleared, 0 hard-gate failures, fairness contract passed, advisory `widening_rate_healthy` remains nonblocking mechanism attention.
- Superseded on 2026-04-18 by B-110-tagged benchmark scenarios: quick `agent_operating_character` now clears hard, secondary, and advisory checks with `odylith_requires_widening_rate=0.0`.
- `PYTHONPATH=src python -m odylith.cli benchmark --repo-root . --profile quick --family guidance_behavior --no-write-report --json`: provisional pass after the learning-spine/explain implementation; 6 selected scenarios, hard quality gate cleared, 0 hard-gate failures, no advisory failures.
- `./.odylith/bin/odylith sync --repo-root . --impact-mode selective --proceed-with-overlap -- ...`: passed after the learning-spine/explain implementation, including plan/workstream binding, backlog contract, Registry contract, Atlas review-marker refresh for D-039, Compass, Radar, Registry, Casebook, shell render, source bundle mirror, delivery intelligence refresh, and Registry forensics updates.
- `./.odylith/bin/odylith atlas auto-update --repo-root . --all-stale --runtime-mode standalone`: passed after sync; refreshed review markers for D-001 and D-027 and brought Atlas to 39 fresh / 0 stale.
- `./.odylith/bin/odylith sync --repo-root . --check-only --impact-mode selective --proceed-with-overlap`: passed after Atlas settlement; Registry, backlog, plan, Atlas, and delivery-intelligence checks are green.
- `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_context_execution_alignment_browser.py tests/integration/runtime/test_intervention_visibility_browser.py tests/integration/runtime/test_compass_browser_regression_matrix.py tests/integration/runtime/test_atlas_sort_browser.py tests/integration/runtime/test_casebook_sort_browser.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`: 158 passed, 1 skipped after the latest governed refresh.
- Final Atlas settlement: `./.odylith/bin/odylith atlas auto-update --repo-root . --all-stale --runtime-mode standalone` refreshed D-001 review markers and brought Atlas to 39 fresh / 0 stale; the immediate follow-up `./.odylith/bin/odylith sync --repo-root . --check-only --impact-mode selective --proceed-with-overlap` passed.
- Final narrow surface verification after Atlas settlement: `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_atlas_sort_browser.py`: 23 passed.
- 2026-04-18 hardening pass:
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_intervention_alignment_evidence.py`: 39 passed after open-world pressure, proof-obligation, live-voice, and platform-integration hardening.
  - `./.odylith/bin/odylith validate agent-operating-character --repo-root . --json`: passed with 19 selected cases, platform integration passing, all declared corpus expectations matched, `character_provider_call_count=0`, and `character_host_model_call_count=0`.
  - `./.odylith/bin/odylith validate guidance-behavior --repo-root .`: passed with 6 cases and 11 guidance checks.
  - `PYTHONPATH=src python -m py_compile src/odylith/runtime/character/*.py src/odylith/runtime/governance/validate_agent_operating_character.py src/odylith/runtime/intervention_engine/alignment_evidence.py src/odylith/runtime/execution_engine/runtime_surface_governance.py src/odylith/cli.py`: passed.
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_execution_engine.py tests/unit/runtime/test_execution_engine_handshake.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_intervention_alignment_evidence.py tests/unit/test_cli.py tests/unit/test_cli_audit.py -k 'character or agent_operating_character or guidance_behavior or execution_engine or intervention or context_packet or memory'`: 141 passed, 427 deselected.
  - `./.odylith/bin/odylith benchmark --repo-root . --profile quick --family agent_operating_character --no-write-report --json`: superseded by the latest B-110-tagged quick run where advisory checks clear and `odylith_requires_widening_rate=0.0`.
  - `./.odylith/bin/odylith benchmark --repo-root . --profile quick --family guidance_behavior --no-write-report --json`: provisional pass, hard quality gate cleared, 0 hard-gate failures, fairness passed, advisory checks clear.
- 2026-04-18 final post-sync QA:
  - `./.odylith/bin/odylith sync --repo-root . --impact-mode selective --proceed-with-overlap -- ...`: passed; refreshed Registry forensics, Compass, Radar, Registry, Casebook, Atlas, shell, delivery intelligence, and bundle mirrors; Atlas settled at 39 fresh / 0 stale.
  - `./.odylith/bin/odylith sync --repo-root . --check-only --impact-mode selective --proceed-with-overlap`: passed after governed refresh.
  - `./.odylith/bin/odylith validate agent-operating-character --repo-root . --json`: passed after sync; 19 cases, platform integration passed, all declared expectation checks matched, `character_provider_call_count=0`, `character_host_model_call_count=0`, and hot-path budget pass rate 1.0.
  - `./.odylith/bin/odylith validate guidance-behavior --repo-root .`: passed after sync; 6 cases and 11 guidance checks.
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_execution_engine.py tests/unit/runtime/test_execution_engine_handshake.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_tooling_context_routing.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_isolation.py tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_intervention_alignment_evidence.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py tests/unit/install/test_codex_project_assets.py tests/unit/test_cli.py tests/unit/test_cli_audit.py`: 626 passed.
  - `./.odylith/bin/odylith benchmark --repo-root . --profile quick --family agent_operating_character --no-write-report --json`: `report_id=0d3192435b70c663`, provisional pass, 7 scenarios, hard quality gate cleared, secondary guardrails cleared, fairness passed; superseded by `report_id=2fca44b29de6d155` with advisory checks clear.
  - `./.odylith/bin/odylith benchmark --repo-root . --profile quick --family guidance_behavior --no-write-report --json`: `report_id=f7847a19c3c8d017`, provisional pass, 6 scenarios, hard quality gate cleared, secondary guardrails cleared, advisory checks clear, fairness passed.
  - `PYTHONPATH=src pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_context_execution_alignment_browser.py tests/integration/runtime/test_intervention_visibility_browser.py tests/integration/runtime/test_compass_browser_regression_matrix.py tests/integration/runtime/test_atlas_sort_browser.py tests/integration/runtime/test_casebook_sort_browser.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`: 158 passed, 1 skipped.
  - Final selective sync exposed and fixed a refresh-step executor bug where structured Compass refresh dictionaries crashed `odylith sync` instead of becoming an exit status. `PYTHONPATH=src pytest -q tests/unit/runtime/test_sync_cli_compat.py -k 'run_callable_with_heartbeat or dashboard_refresh or selective'`: 21 passed, 35 deselected; `PYTHONPATH=src python -m py_compile src/odylith/runtime/governance/sync_workstream_artifacts.py`: passed.
- 2026-04-18 aggressive QA follow-up:
  - Added edge coverage for visible-intervention proof-gathering commands, evidence-backed visible claims, transcript-like source-ref suppression, non-integer practice-event counters, malformed hot-path budget counters, queued structured refresh results, and dashboard structured failure results without explicit `rc`.
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_sync_cli_compat.py -k 'character or agent_operating_character or run_callable_with_heartbeat or dashboard_refresh or selective'`: 61 passed, 35 deselected.
  - `PYTHONPATH=src python -m py_compile src/odylith/runtime/character/*.py src/odylith/runtime/governance/validate_agent_operating_character.py src/odylith/runtime/governance/sync_workstream_artifacts.py`: passed.
  - `./.odylith/bin/odylith validate agent-operating-character --repo-root . --json`: passed; 19 cases, platform integration passed, hot-path provider calls 0, hot-path host model calls 0, hot-path budget pass rate 1.0.
  - `./.odylith/bin/odylith validate guidance-behavior --repo-root .`: passed; 6 cases and 11 guidance checks.
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_execution_engine.py tests/unit/runtime/test_execution_engine_handshake.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_tooling_context_routing.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_isolation.py tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_intervention_alignment_evidence.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py tests/unit/install/test_codex_project_assets.py tests/unit/test_cli.py tests/unit/test_cli_audit.py tests/unit/runtime/test_sync_cli_compat.py`: 690 passed.
- 2026-04-18 adaptive materialization hardening:
  - Centralized pressure/law signal extraction in
    `src/odylith/runtime/character/signals.py` and moved hard-law recovery
    actions, cues, decision semantics, and visible-intervention law ownership
    into `contract.py`.
  - Added adaptive affordance ranking for systemic integration pressure,
    live/non-templated voice pressure, learning feedback, recurrence, and
    urgency so admissible open-world pressure gets a useful local next move
    instead of generic action or rigid named posture routing.
  - Tightened benchmark public-claim detection so benchmark feedback and
    learning work stay admissible, while README/release/public shipped-claim
    pressure still blocks until benchmark proof exists.
  - Hardened compact practice memory to suppress transcript/secret-like refs
    and ephemeral source refs such as `/tmp`, `/var/folders`, `/private/var`,
    and `/dev/fd`, and hardened validation to reject unsafe source refs that
    reach a practice event.
  - Tagged all `guidance_behavior` and `agent_operating_character` quick
    benchmark scenarios to B-110 in source and bundle corpus mirrors, removing
    false advisory widening from the B-110 proof lane.
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py`: 41 passed for non-rigid behavior, learning-feedback affordances, hard-law policy coverage, and ephemeral source-ref filtering.
  - `PYTHONPATH=src pytest -q tests/unit/runtime`: 2113 passed.
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_validate_guidance_behavior.py`: 80 passed after B-110 corpus tagging.
  - `./.odylith/bin/odylith validate agent-operating-character --repo-root .`: passed.
  - `./.odylith/bin/odylith validate guidance-behavior --repo-root .`: passed.
  - `./.odylith/bin/odylith benchmark --profile quick --family agent_operating_character --no-write-report --json`: `report_id=2fca44b29de6d155`, provisional pass, 7 scenarios, hard quality gate cleared, secondary guardrails cleared, advisory checks cleared, fairness passed, `odylith_requires_widening_rate=0.0`.
  - `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior --no-write-report --json`: `report_id=bc167789af1df105`, provisional pass, 6 scenarios, hard quality gate cleared, secondary guardrails cleared, advisory checks cleared, fairness passed, `odylith_requires_widening_rate=0.0`.
- 2026-04-18 post-sync proof:
  - `./.odylith/bin/odylith sync --repo-root . --impact-mode selective --proceed-with-overlap`: passed; refreshed Registry forensics, Atlas, Compass, Radar, Registry, Casebook, shell, delivery intelligence, and source bundle mirrors; Atlas reported 39 fresh / 0 stale.
  - `PYTHONPATH=src pytest -q tests/unit/runtime`: 2113 passed after governed refresh and bundle mirror settlement.
  - `./.odylith/bin/odylith validate agent-operating-character --repo-root .`: passed after sync.
  - `./.odylith/bin/odylith validate guidance-behavior --repo-root .`: passed after sync.
  - `./.odylith/bin/odylith benchmark --profile quick --family agent_operating_character --no-write-report --json`: `report_id=db72f40e8035386e`, provisional pass, 7 scenarios, hard quality gate cleared, secondary guardrails cleared, advisory checks cleared, fairness passed, `odylith_requires_widening_rate=0.0`.
  - `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior --no-write-report --json`: `report_id=f44966389e8c775f`, provisional pass, 6 scenarios, hard quality gate cleared, secondary guardrails cleared, advisory checks cleared, fairness passed, `odylith_requires_widening_rate=0.0`.
  - `PYTHONPATH=src pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_context_execution_alignment_browser.py tests/integration/runtime/test_intervention_visibility_browser.py tests/integration/runtime/test_compass_browser_regression_matrix.py tests/integration/runtime/test_atlas_sort_browser.py tests/integration/runtime/test_casebook_sort_browser.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`: 158 passed, 1 skipped.
- 2026-04-18 aggressive false-block and credit-safety hardening:
  - Centralized negation-aware signal handling for delegation, queue adoption,
    model-credit spend, public-claim proof execution, and CLI-owned governed
    truth. The runtime now admits preventive discipline work such as "do not
    spawn subagents", "zero host model calls", and "run release proof" while
    preserving hard blocks/defer decisions for the unsafe moves themselves.
  - Added five Agent Operating Character corpus cases for allowed technical
    plan authoring, release-proof execution, credit-safety work, negated
    delegation, and modern Codex model aliases. Corpus source and bundle mirror
    now carry 24 deterministic cases.
  - Hardened host-family normalization so modern Codex and Claude model aliases
    resolve to shared Codex/Claude family contracts without treating model
    names as model-consuming decision engines.
  - Hardened benchmark metric summaries to publish false allow/block,
    unknown-pressure handling, stance-vector, noise-suppression, intervention
    precision, and unseen-pressure generalization rates from deterministic
    Character case results.
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py`: 48 passed.
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_validate_guidance_behavior.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_runner.py`: 225 passed.
  - `PYTHONPATH=src pytest -q tests/unit/runtime`: 2120 passed.
  - `./.odylith/bin/odylith validate agent-operating-character --repo-root .`: passed, 24 cases, zero host/provider calls.
  - `./.odylith/bin/odylith validate guidance-behavior --repo-root .`: passed.
  - `./.odylith/bin/odylith benchmark --profile quick --family agent_operating_character --no-write-report --json`: `report_id=1be88ce4ead87770`, provisional pass, 7 scenarios, hard quality gate cleared, secondary guardrails cleared, advisory checks cleared, fairness passed, `odylith_requires_widening_rate=0.0`.
  - `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior --no-write-report --json`: `report_id=61d3b6a2b1cbe33e`, provisional pass, 6 scenarios, hard quality gate cleared, secondary guardrails cleared, advisory checks cleared, fairness passed, `odylith_requires_widening_rate=0.0`.
- 2026-04-18 post-refresh QA:
  - `./.odylith/bin/odylith sync --repo-root . --impact-mode selective --proceed-with-overlap`: passed; refreshed Compass, Radar, Registry, Casebook, Atlas, shell, delivery intelligence, and bundle mirrors; Atlas reported 39 fresh / 0 stale.
  - `./.odylith/bin/odylith sync --repo-root . --check-only --impact-mode selective --proceed-with-overlap`: passed.
  - `./.odylith/bin/odylith validate agent-operating-character --repo-root .`: passed.
  - `./.odylith/bin/odylith validate guidance-behavior --repo-root .`: passed.
  - `PYTHONPATH=src pytest -q tests/unit/runtime/test_agent_operating_character.py tests/unit/runtime/test_validate_agent_operating_character.py tests/unit/runtime/test_validate_guidance_behavior.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_runner.py`: 273 passed.
  - `PYTHONPATH=src pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_atlas_sort_browser.py tests/integration/runtime/test_casebook_sort_browser.py tests/integration/runtime/test_surface_browser_layout_audit.py`: 61 passed.
  - Post-refresh quick `agent_operating_character`: `report_id=e54e6fe7c7f3b52b`, provisional pass, hard/secondary/advisory gates true, `odylith_requires_widening_rate=0.0`, validation delta `0.714`, critical validation delta `0.714`.
  - Post-refresh quick `guidance_behavior`: `report_id=e705091798cd46fd`, provisional pass, hard/secondary/advisory gates true, `odylith_requires_widening_rate=0.0`, validation delta `1.0`, critical validation delta `1.0`.

## Implementation Evidence
- Added `src/odylith/runtime/character/` as the shared adaptive, zero-credit runtime package instead of scattering checks through host adapters.
- Added `odylith/runtime/source/agent-operating-character-evaluation-corpus.v1.json` and bundle mirror under `src/odylith/bundle/assets/odylith/runtime/source/`.
- Added `odylith validate agent-operating-character` and `odylith character status/check/explain`.
- Kept `odylith validate guidance-behavior` intact and made it the first deterministic pressure-family validator under Adaptive Agent Operating Character.
- Added `agent_operating_character` benchmark family, taxonomy/rules integration, quick local-only selection, and source/bundle benchmark corpus entries.
- Added `odylith_agent_operating_character_host_lane_support.v1` and explicit
  validator/corpus coverage for Codex and Claude across dev, dogfood, and
  consumer lanes, including host-model alias normalization without credit burn.
- Added `supported_host_lane` as a hard-law guard so unsupported hosts or lanes
  cannot silently admit work, while known Codex/Claude and dev/dogfood/consumer
  aliases continue to normalize through the shared contract.
- Added `src/odylith/runtime/character/memory.py` for compact, sanitized
  practice-event shaping under the learning contract. The event keeps pressure
  features, stance, hard laws, recovery action, proof obligation, budget
  counters, retention class, and fingerprints, while dropping secret-like refs
  and raw transcript payloads.
- Added focused proof and voice helpers so proof obligations are reusable and
  intervention candidates stay evidence-shaped: Character now emits explicit
  obligations such as `visible_intervention_proof_required`,
  `matched_benchmark_proof_required`, or `bounded_delegation_contract_required`
  and leaves final human copy to the intervention engine.
- Hardened open-world pressure extraction so systemic integration, templated
  voice, learning feedback, reliability, and refactor pressure influence the
  stance vector without becoming closed posture states or blocking low-risk
  action by default.
- Tightened false-positive boundaries: CLI-backed backlog authoring no longer
  trips queue adoption or governed-truth shortcut laws, while hand-authored
  governed truth, proofless completion, visible-intervention overclaim, public
  product claim, and host-model-credit paths remain deterministic gates.
- Tightened visible-intervention boundaries again so proof-gathering commands
  such as `intervention-status` and `visible-intervention` remain admissible
  silent local actions, while actual visible-UX claims still require proven
  visibility or rendered fallback evidence.
- Character validation now checks declared corpus obligations instead of only
  shape: expected decision, pressure observations, required tool affordance,
  proof obligation, memory signal, learning outcome, intervention visibility,
  zero-copy voice policy, host/lane parity, bundle mirrors, benchmark family,
  and platform integration across Context, Execution, Memory, Intervention,
  and Benchmark.
- Intervention alignment now treats `agent_operating_character_contract` as a
  first-class evidence class. Passing Character summaries stay quiet; failing
  summaries become a single high-signal invariant fact instead of chat noise.
- `odylith character check` now records local decision receipts under
  `.odylith/cache/agent-operating-character/decisions`, and
  `odylith character explain` turns those receipts into a concise evidence,
  recovery, learning, and budget explanation.
- `odylith character status` now reports runtime summary, active hard laws,
  learning outcomes and retention classes, benchmark-proof freshness posture,
  and the last local decision digest.
- Hardened the validator against malformed benchmark assertions, unsupported
  learning outcomes, unsupported host/lane assertions, invalid credit counters,
  and non-object evidence payloads.
- Hardened the validator to require the compact practice-event contract and to
  fail if practice events omit required fields, use unknown learning outcomes
  or retention classes, retain transcript/secret material, disagree with the
  decision payload, or report non-zero hot-path credit counters.
- Hardened compact memory and validator handling for transcript-shaped refs and
  malformed counter payloads: transcript-like source refs are suppressed from
  practice events, non-integer counters become validation issues instead of
  tracebacks, and hot-path budget failure detection now fails closed on bad
  counter values.
- Refactored proof obligations into `src/odylith/runtime/character/proof.py`
  so hard-law failures produce reusable, canonical obligations instead of
  scattered prose strings.
- Refactored Character intervention shaping into
  `src/odylith/runtime/character/voice.py`. Character emits evidence,
  recovery affordances, visibility-proof needs, and owner-surface metadata,
  while Intervention and Chatter retain live human wording and avoid
  mechanical template copy.
- Refined open-world pressure extraction and hard-law applicability so
  systemic integration, learning feedback, voice-template risk, reliability,
  and refactor pressure can alter stance without becoming a closed posture
  state machine, while CLI-backed backlog authoring no longer false-blocks as
  queue adoption or governed-truth bypass.
- Made visible-intervention overclaim a hard block until status proof,
  transcript confirmation, or rendered fallback exists.
- Expanded deterministic Character validation to enforce corpus-declared
  expected decisions, pressure observations, ranked affordances, proof
  obligations, learning outcomes, memory signals, intervention visibility,
  bundle mirrors, platform integration, and zero-copy voice policy.
- Added platform integration checks for Context, Execution, Memory,
  Intervention, and Benchmark so Agent Operating Character cannot pass as an
  isolated corpus validator while the rest of Odylith is disconnected.
- Integrated Character evidence into Execution Engine runtime-surface
  governance and Intervention alignment evidence, preserving local-only
  summaries and avoiding host probes, provider calls, full validation, and
  broad scans on the hot path.
- Hardened governed sync callable-step execution so structured refresh runtime
  results are coerced into pass/fail exit codes, preventing Compass or other
  refresh dictionaries from crashing selective sync while still failing closed
  on unknown or failed status payloads.
- Hardened dashboard refresh structured-result handling so queued refresh
  results are non-failure, failed structured results without an explicit `rc`
  fail closed, and sync no longer treats malformed refresh payloads as either
  crashes or false green surface updates.
- Hardened the Compass browser-test narrator fixture so evolving governed
  product language is normalized into plain maintainer wording before the
  standup validator runs; this keeps surface regression tests focused on
  runtime behavior while preserving the product validator's rejection of
  stagey voice.
- Made character decision ids deterministic for evidence maps whose keys collide
  after stringification, avoiding salted or order-sensitive IDs under edge input.
- Connected compact `character_summary` through Context Engine packets, execution handshake summaries, memory contracts, benchmark packet observation, and recommended validation commands.
- Updated shared guidance, Codex and Claude host contracts, skills, Registry component specs, Atlas D-039 topology, Compass log, Radar B-110 program surfaces, and shipped bundle mirrors.

## Release Gates
- Pinned dogfood runtime integrity must be restored before shipped-runtime proof is claimed.
- No governed truth is hand-authored where a working CLI writer exists.
- No red-zone source file receives substantive character logic; oversized front doors get dispatch-only edits.
- Full v0.1.11 public claims require full proof benchmark with matched `odylith_on` versus `raw_agent_baseline`, warm and cold profiles, fairness intact, and no stale proof aliases.
