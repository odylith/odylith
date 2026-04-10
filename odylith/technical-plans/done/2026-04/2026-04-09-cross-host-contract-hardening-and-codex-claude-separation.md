Status: Done

Created: 2026-04-09

Updated: 2026-04-09

Backlog: B-069

Goal: Separate host capability, model-family policy, shared product guidance,
and proof publication so Odylith behaves as one product across Codex and
Claude Code without leaking Codex-only canon into shared runtime surfaces.

Assumptions:
- Claude Code already deserves the same grounding, reasoning, and UX quality
  bar even though native spawn is not yet a proven host capability there.
- Published benchmark proof must stay explicitly host-scoped until Claude has
  its own measured evidence lane.
- Compatibility aliases are cheaper than attempting a repo-wide all-or-nothing
  rename in one step.

Constraints:
- Do not mutate `.odylith/*` local caches or archived proof outputs.
- Keep Codex-only behavior keyed to `model_family=codex` or explicit transport
  capabilities, not ambient string assumptions.
- Rewrite normative governance and product-contract language, but keep factual
  historical evidence truthful.
- Regenerate bundle mirrors from source truth rather than maintaining
  divergent copies by hand.

Reversibility: The new canonical ids and stream names are additive behind
compatibility readers for one release cycle, so the rollout can be paused or
partially reverted without making older runtime history unreadable.

Boundary Conditions:
- Scope includes host adapter/runtime contracts, routing/orchestration/context
  summaries, Compass runtime canon, benchmark proof schema, shared docs,
  Registry specs, Atlas diagrams, and bundled mirrors.
- Scope excludes claiming Claude-native spawn support, changing archived
  history, or publishing Claude benchmark proof without fresh measurement.

Related Bugs:
- [CB-084](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-host-contract-drift-leaks-codex-only-policy-into-claude-and-shared-runtime-surfaces.md)
- [CB-072](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-08-release-proof-tests-assume-local-codex-host-and-break-in-github-actions.md)
- [CB-089](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-benchmark-live-proof-reports-still-emit-codex-branded-canonical-fields.md)

## Learnings
- [x] The product already has cross-host capability in more places than the
      current canon admits.
- [x] Host transport capability and model-family defaults are separate
      contracts and should not keep sharing one switch.

## Must-Ship
- [x] Wave 1: add the canonical host capability contract and route all
      Codex-specific behavior through `model_family=codex` or explicit
      transport capabilities.
- [x] Wave 1: replace canonical routed profile ids with
      `analysis_medium`, `analysis_high`, `fast_worker`, `write_medium`,
      `write_high`, `frontier_high`, and `frontier_xhigh`, while accepting the
      legacy ids on read.
- [x] Wave 1: rename Compass runtime canon to `agent-stream.v1.jsonl`,
      `recent_agent_events`, `agent_stream`, and a neutral hot-path label
      while keeping legacy `codex-*` readers.
- [x] Wave 2: rewrite CLI, install, `on`, `off`, shared guidance, and root
      docs to use explicit host-matrix language instead of Codex-default copy.
- [x] Wave 2: update Registry specs for `odylith`, `odylith-context-engine`,
      `subagent-router`, `subagent-orchestrator`, `compass`, and `benchmark`,
      plus Atlas diagrams `D-002`, `D-012`, `D-014`, and `D-024`.
- [x] Split the remaining benchmark report-field and live-runner schema
      normalization into `B-070` so this slice can close truthfully on the
      non-benchmark host contract.
- [x] Regenerate bundle mirrors and current rendered artifacts from updated
      source truth only.

## Should-Ship
- [x] Update legacy workstream records `B-012`, `B-015`, `B-016`, and `B-031`
      so their Codex-first language is marked historical and no longer reads
      like the current product contract.
- [x] Add focused host-capability tests for unknown-host fail-closed behavior
      so new integrations do not silently inherit Codex defaults.
- [x] Keep Compass author/source/session metadata derived from the resolved
      host runtime instead of defaulting to `codex`.

## Defer
- [x] Claude-native native-spawn transport work until a dedicated proof slice
      exists.
- [x] Multi-host benchmark publication tables beyond the current Codex-scoped
      public proof.
- [x] Benchmark live-runner host labels, canonical benchmark token fields, and
      graph/test alias cleanup moved to `B-070`.

## Success Criteria
- [x] Shared runtime contracts stop using Codex names as the canonical public
      ids.
- [x] Claude Code keeps parity on grounding, reasoning, and UX surfaces that
      do not depend on native spawn.
- [x] Codex-specific proof and transport language survives only where it is
      factually required.
- [x] Strict sync passes after source, rendered artifacts, and bundled mirrors
      are regenerated.

## Non-Goals
- [x] Replacing truthful Codex-specific benchmark history with invented
      cross-host proof.
- [x] Editing archived runtime history snapshots.
- [x] Broadening compatibility by silently weakening validation.

## Open Questions
- [x] Legacy alias emission duration remains deferred to `B-070` because the
      remaining decision now only affects benchmark payloads.
- [x] Whether benchmark should expose a dedicated
      `published_proof_host_family` field is deferred to `B-070`.

## Impacted Areas
- [x] [2026-04-09-cross-host-contract-hardening-and-codex-claude-separation.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-09-cross-host-contract-hardening-and-codex-claude-separation.md)
- [x] [2026-04-09-benchmark-host-family-proof-canon-and-live-runner-schema-normalization.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-09-benchmark-host-family-proof-canon-and-live-runner-schema-normalization.md)
- [x] [2026-04-09-cross-host-contract-hardening-and-codex-claude-separation.md](/Users/freedom/code/odylith/odylith/technical-plans/done/2026-04/2026-04-09-cross-host-contract-hardening-and-codex-claude-separation.md)
- [x] [2026-04-09-host-contract-drift-leaks-codex-only-policy-into-claude-and-shared-runtime-surfaces.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-host-contract-drift-leaks-codex-only-policy-into-claude-and-shared-runtime-surfaces.md)
- [x] [2026-04-09-benchmark-live-proof-reports-still-emit-codex-branded-canonical-fields.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-benchmark-live-proof-reports-still-emit-codex-branded-canonical-fields.md)
- [x] [host_adapter.py](/Users/freedom/code/odylith/src/odylith/contracts/host_adapter.py)
- [x] [host_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/common/host_runtime.py)
- [x] [subagent_router.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_router.py)
- [x] [subagent_orchestrator.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_orchestrator.py)
- [x] [tooling_context_routing.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/tooling_context_routing.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [tooling_memory_contracts.py](/Users/freedom/code/odylith/src/odylith/runtime/memory/tooling_memory_contracts.py)
- [x] [log_compass_timeline_event.py](/Users/freedom/code/odylith/src/odylith/runtime/common/log_compass_timeline_event.py)
- [x] [odylith_context_engine_projection_search_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_projection_search_runtime.py)
- [x] [odylith_reasoning.py](/Users/freedom/code/odylith/src/odylith/runtime/reasoning/odylith_reasoning.py)
- [x] [README.md](/Users/freedom/code/odylith/README.md)
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [SUBAGENT_ROUTING_AND_ORCHESTRATION.md](/Users/freedom/code/odylith/odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md)
- [x] [PRODUCT_SURFACES_AND_RUNTIME.md](/Users/freedom/code/odylith/odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md)
- [x] [DELIVERY_AND_GOVERNANCE_SURFACES.md](/Users/freedom/code/odylith/odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md)
- [x] [ODYLITH_CONTEXT_ENGINE.md](/Users/freedom/code/odylith/odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/subagent-router/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/benchmark/CURRENT_SPEC.md)
- [x] [AGENTS.md](/Users/freedom/code/odylith/odylith/compass/runtime/AGENTS.md)
- [x] [agent-stream.v1.jsonl](/Users/freedom/code/odylith/odylith/compass/runtime/agent-stream.v1.jsonl)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/contracts/test_contracts.py tests/unit/runtime/test_subagent_reasoning_ladder.py tests/unit/runtime/test_tooling_context_routing.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_odylith_context_engine_store.py tests/unit/runtime/test_host_runtime_contract.py`
      (`104 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_reasoning.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_update_compass.py tests/integration/runtime/test_surface_browser_deep.py`
      (`153 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_shell_onboarding.py tests/integration/install/test_bundle.py`
      (`102 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_sync_component_spec_requirements.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_mermaid_catalog.py`
      (`62 passed`)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
      (passed)
- [x] `git diff --check`
      (passed)

## Current Outcome
- [x] `B-069` is closed for the non-benchmark cross-host contract surface.
- [x] Host capability, routing, Compass canon, shared guidance, Registry truth,
      Atlas diagrams, and bundled mirrors now use the host-neutral contract and
      keep Codex-specific behavior behind explicit capability or
      `model_family=codex`.
- [x] The canonical current Compass runtime stream now exists at
      `odylith/compass/runtime/agent-stream.v1.jsonl` while legacy
      `codex-stream.v1.jsonl` remains readable.
- [x] The remaining benchmark-only host-canon schema work is explicitly split
      into `B-070` / `CB-089` instead of being left as an unfinished hidden
      tail inside this closed plan.
