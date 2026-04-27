---
status: finished
idea_id: B-069
title: Cross-Host Contract Hardening and Codex-Claude Separation
date: 2026-04-09
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: host adapter/runtime capability contract, subagent router and orchestrator execution profiles, Context Engine routing and memory contracts, Compass runtime stream and payloads, CLI and install guidance, registry and Atlas governance, bundled consumer mirrors, and benchmark follow-up boundary setting
sizing: L
complexity: VeryHigh
ordering_score: 95
ordering_rationale: Odylith already shares major grounding, reasoning, and UI surfaces across Codex and Claude Code, but too much product truth still treats Codex naming and transport assumptions as the canonical contract. Until host capability, model family, runtime copy, and proof fields are separated cleanly, Claude parity stays brittle, Compass and benchmark readouts keep leaking Codex-only language, and maintainers cannot distinguish real transport differences from accidental host drift.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-09-cross-host-contract-hardening-and-codex-claude-separation.md
execution_model: standard
workstream_type: umbrella
workstream_parent:
workstream_children: B-070
workstream_depends_on: B-027,B-061,B-067
workstream_blocks:
related_diagram_ids: D-002,D-012,D-014,D-024
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into: B-070
workstream_merged_into:
workstream_merged_from:
supersedes: B-012,B-015,B-016,B-031
superseded_by:
---

## Closeout Note
This umbrella closed on 2026-04-09 after the shared runtime, governance, UX,
and current-surface host-separation work passed focused regression and strict
sync proof. The remaining benchmark live-runner and report-field canon
normalization moved into `B-070` so the benchmark-only schema tail does not
leave the broader product contract half-open.

## Problem
Odylith's runtime and governance layers still carry hardcoded Codex-first
policy in places that should be host-neutral. Host detection often doubles as
policy, canonical execution-profile ids still encode Codex model branding,
Compass runtime artifacts still use Codex stream names, and guidance plus
proof surfaces still frame Codex behavior as the default product contract even
when Claude Code already shares the same grounding and reasoning quality bar.

That drift makes Claude compatibility feel partial even where the product
already works, while also obscuring the real boundary: native spawn is a host
capability question, not the whole product contract.

## Customer
- Primary: Odylith operators who want the same product outcome in Codex and
  Claude Code without hidden contract drift.
- Secondary: maintainers who need host capability, model-family defaults, and
  benchmark publication scope to stay explicit and auditable.

## Opportunity
If Odylith makes host capability the canonical runtime contract and treats
Codex-only behavior as one scoped model-family policy instead of the global
default, the product can keep Codex-native delegation where it truly exists
while making Claude Code feel like a first-class supported host across docs,
grounding, Compass, governance, and benchmark scaffolding.

## Proposed Solution
Add one canonical host capability contract that separates host family,
transport capabilities, and model-family behavior; switch runtime routing and
execution-profile ids to host-neutral canon with compatibility aliases; rename
Compass runtime artifacts to host-neutral stream terms while keeping legacy
read compatibility; rewrite source governance and docs around a host matrix;
and normalize benchmark/proof fields so published proof can stay Codex-scoped
without making the shared product contract Codex-scoped.

## Scope
- add explicit `model_family`, `supports_native_spawn`,
  `supports_local_structured_reasoning`, and
  `supports_explicit_model_selection` fields to the host adapter/runtime
  contract
- make routing, orchestration, context-engine summaries, and memory/tooling
  contracts emit host-neutral profile ids and capability-aware behavior
- rename Compass stream and hot-path canon to `agent-*` terms while keeping
  readers compatible with legacy `codex-*` artifacts
- keep local structured reasoning on both hosts while scoping Codex model
  aliases to `model_family=codex`
- rewrite shared guidance, install/on/off messaging, component specs, Atlas
  diagrams, and Radar or Casebook truth around explicit host separation
- add host-neutral benchmark report fields while preserving Codex-scoped
  published proof until Claude has measured proof of its own
- regenerate bundled mirrors and checked-in surface payloads from the updated
  source truth only

## Non-Goals
- claiming native spawn parity for Claude Code before it is proven
- retro-editing archived Compass history or local `.odylith` benchmark outputs
- weakening Codex-specific proof claims that remain factually Codex-scoped

## Risks
- compatibility aliases could be incomplete and break older runtime or test
  readers
- governance rewrites could accidentally rewrite factual historical evidence
  instead of only the normative contract
- host-neutral copy could hide a real transport limitation if the capability
  matrix is not explicit enough

## Dependencies
- `B-027` established the lane and toolchain boundary language this slice now
  needs to generalize across hosts
- `B-061` split reasoning boundaries and already introduced shared local
  provider structure that this slice must keep honest
- `B-067` decomposed the Context Engine and made host-contract drift easier to
  fix centrally instead of through one oversized module

## Success Metrics
- Codex-only behavior is keyed off `model_family=codex` or explicit transport
  capabilities instead of ambient string checks
- canonical routed profile ids and Compass stream names are host-neutral while
  legacy readers remain compatible
- shared docs, install messaging, and Registry truth describe one host matrix
  instead of scattering Codex-only caveats through the product
- benchmark reports expose host-neutral canonical fields while published proof
  stays honestly host-scoped

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/contracts/test_contracts.py tests/unit/runtime/test_subagent_reasoning_ladder.py tests/unit/runtime/test_tooling_context_routing.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_odylith_context_engine_store.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_reasoning.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_update_compass.py tests/integration/runtime/test_surface_browser_deep.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_shell_onboarding.py tests/integration/install/test_bundle.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_live_execution.py tests/unit/runtime/test_odylith_benchmark_graphs.py tests/unit/runtime/test_hygiene.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_sync_component_spec_requirements.py tests/unit/runtime/test_render_registry_dashboard.py`
- `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- `git diff --check`

## Rollout
Execute in three waves under one umbrella:
1. host capability and runtime contract hardening
2. shared surface, governance, and UX rewrite
3. benchmark and proof normalization with compatibility shims

Waves 1 and 2 plus the non-benchmark governance closeout landed in this slice.
The remaining benchmark-only schema and proof-field migration moved to `B-070`
before closeout.

Do not mutate `.odylith/*` caches or archived proof outputs as part of this
rollout. Regenerate only source-owned current artifacts and bundle mirrors.

## Why Now
Odylith is already claiming shared product value across Codex and Claude Code.
Leaving Codex-only naming and policy wired into the canon now will only make
later Claude parity and proof work noisier, riskier, and more expensive.

## Product View
Host neutrality is not a doc polish task. It is the product contract that lets
Odylith keep one intelligence plane while telling the truth about which host
can transport which kind of delegation today.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `subagent-router`
- `subagent-orchestrator`
- `compass`
- `benchmark`

## Interface Changes
- host adapter payloads gain explicit capability and `model_family` fields
- routed execution-profile canon changes to host-neutral ids with compatibility
  aliases
- Compass runtime canon prefers `agent-stream.v1.jsonl` while reading legacy
  `codex-stream.v1.jsonl`
- benchmark reports add host-neutral canonical fields alongside temporary
  compatibility aliases

## Migration/Compatibility
- keep legacy routed profile ids readable for one compatibility release
- keep legacy Compass runtime stream names readable while source-owned current
  artifacts move to the new canon
- keep historical facts truthful while rewriting old normative product
  language to point at this umbrella workstream

## Test Strategy
- add direct host-capability matrix coverage for Codex, Claude, and unknown
  hosts
- prove shared reasoning, Compass, CLI, install, Registry, and benchmark
  surfaces against the new host-neutral canon
- finish with strict sync proof so governance source and bundled mirrors stay
  aligned

## Open Questions
- whether Claude-native transport delegation earns its own future child slice
  once explicit proof exists
- whether any external/public benchmark tables should show a second host lane
  before Claude has host-matched measured proof

## Outcome
- shared runtime, guidance, Compass, Registry, Atlas, and bundled-surface
  canon now key Codex-specific behavior off `model_family=codex` or explicit
  transport capability instead of ambient Codex-default naming
- current source-owned governance and UX surfaces passed strict standalone sync
  proof after the host-neutral contract rewrite
- the remaining benchmark report-field and live-runner schema tail moved to
  `B-070` instead of staying hidden inside the finished cross-host contract
  umbrella
