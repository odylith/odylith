---
status: implementation
idea_id: B-072
title: Execution Governance Engines, Admissibility Control, and Constraint-Aware Action Runtime
date: 2026-04-09
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: execution-governance runtime package, task contract and admissibility policy, frontier and resumability contracts, resource closure and contradiction checks, external dependency adapters, program and wave ergonomics sidecar, Radar/Compass/Context Engine read models, Registry component boundaries, and Atlas execution topology
sizing: XL
complexity: VeryHigh
ordering_score: 70
ordering_rationale: Odylith is already reasonably strong at grounding and context routing, but its dominant failure mode is still execution governance. Until the product materializes a contract-aware execution runtime that blocks non-admissible next moves, operator trust will keep failing in the same domain-independent way even when the agent already has enough context.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-09-execution-governance-engines-admissibility-control-and-constraint-aware-action-runtime.md
execution_model: umbrella_waves
workstream_type: umbrella
workstream_parent:
workstream_children: B-073,B-074,B-075,B-076,B-077,B-078,B-079
workstream_depends_on: B-062,B-063,B-069,B-071
workstream_blocks:
related_diagram_ids: D-002,D-030,D-031
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Odylith already helps agents find the right topology, ownership, history, and
constraints, but it still fails too often after that point. The product does
not yet materialize one hard execution contract, enforce admissibility in
front of tool calls, or keep one truthful frontier once execution has started.

That gap produces the same failure class across coding, incident response,
infra work, migrations, release operations, and research tasks: the agent had
enough context, then took the wrong next action anyway.

## Customer
- Primary: operators using Odylith through coding agents who need the product
  to prevent the wrong next move, not merely explain the repo better.
- Secondary: maintainers who need one host-general execution system that works
  across Codex and Claude Code while still exploiting each detected host and
  model family's real capabilities truthfully.

## Opportunity
Turn Odylith from a context-first assistant into a constraint-aware execution
OS that keeps agents inside an authoritative lane, blocks destructive partial
scope moves, preserves user corrections as hard invariants, and makes waits,
resumes, and contradictions explicit.

## Proposed Solution
- add one first-class `odylith.runtime.execution_engine.*` sibling package with typed
  contracts for task execution governance
- materialize one machine-readable `ExecutionContract` per substantive session
- enforce `admit`, `deny`, or `defer` decisions in front of execution surfaces
- derive one canonical frontier and one truthful next move after starts,
  reruns, failures, and user corrections
- compute resource closure and destructive-subset posture instead of guessing
- normalize external dependency state, typed receipts, and resumability
- synthesize validation matrices and contradiction records from the active
  contract and evidence
- keep the execution core host-general across Codex and Claude Code, then
  adapt policy and model hints only after host and model-family detection
- ship program/wave authoring ergonomics as a sidecar on the same umbrella so
  coding agents can use the execution-wave contract directly instead of
  hand-editing JSON

## Scope
- umbrella workstream `B-072` plus child workstreams `B-073` through `B-079`
- one new execution-governance Registry component and runtime package boundary
- one canonical execution-wave program file under
  `odylith/radar/source/programs/`
- one umbrella-bound technical plan for the authoring slice
- execution-governance runtime types, policy helpers, and minimal host-profile
  aware admissibility primitives
- initial packet-summary plus shared shell or Compass runtime read models for
  execution-governance posture
- sidecar `odylith program ...` and `odylith wave ...` authoring commands that
  sit on top of the existing execution-wave contract
- Atlas refresh for the context/execution split and one dedicated execution
  governance topology diagram

## Non-Goals
- replacing release planning as the product's release-targeting contract
- claiming provider-complete external dependency coverage in v1
- letting Codex-specific transport affordances become the shared execution
  contract for all hosts
- shipping a bigger note-taking or memory-only layer instead of a governed
  execution system

## Risks
- execution-governance policy could become too permissive and fail to block the
  known failure classes it is meant to prevent
- execution-governance policy could become too rigid and block truthful work if
  frontier, host, or resource-closure signals are incomplete
- the sidecar program/wave CLI could drift from the canonical execution-wave
  contract if it is implemented as a parallel schema instead of a thin authoring
  surface
- host-specific optimization could leak back into the shared contract unless
  host detection stays explicit and capability-gated

## Dependencies
- `B-062` established proof-state frontier discipline that execution
  governance must consume rather than replace
- `B-063` established release planning as a separate contract so execution
  sequencing does not collapse into release targeting
- `B-069` established host-neutral Codex/Claude capability contracts that this
  slice must reuse instead of regressing to Codex-default execution policy
- `B-071` established provider-neutral budget classes and shared posture logic
  that execution governance should honor during critical-path mode

## Success Metrics
- off-contract action rate decreases because actions are screened before
  execution
- user corrections mutate hard constraints immediately instead of decaying into
  soft conversational hints
- one canonical frontier is available for every governed execution session
- destructive subset operations are blocked before execution when closure says
  the scope is incomplete or unsafe
- semantic wait states replace generic `running` posture for external work
- reruns attach to receipts and resume handles by default
- coding agents can author and inspect execution-wave programs with direct
  `odylith program` and `odylith wave` commands instead of patching JSON by hand

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_execution_wave_view_model.py tests/unit/runtime/test_release_planning.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_governance.py tests/unit/test_cli.py`
- `PYTHONPATH=src python3 -m odylith.cli validate backlog-contract --repo-root .`
- `PYTHONPATH=src python3 -m odylith.cli validate component-registry --repo-root .`
- `git diff --check`

## Rollout
1. Create the umbrella and child workstream truth, the execution-wave program
   file, and the umbrella-bound technical plan.
2. Add the execution-governance Registry component, runtime package, and Atlas
   topology refresh.
3. Land the thin program/wave authoring sidecar on the existing execution-wave
   contract.
4. Extend packet summaries and shared shell or Compass runtime surfaces with
   the base execution-governance posture fields.
5. Continue deeper downstream consumer and adapter coverage as later child
   waves become active.

## Why Now
Odylith's next-order product problem is no longer "find one more document."
It is "prevent the wrong next thing." If the product keeps strengthening only
grounding and retrieval, the same execution failures will keep reappearing in
every domain.

## Product View
Execution governance is where Odylith either becomes a trustworthy execution
OS or stays a smart context layer that still lets the agent make procedurally
wrong moves.

## Impacted Components
- `execution-governance`
- `odylith-context-engine`
- `delivery-intelligence`
- `proof-state`
- `subagent-router`
- `subagent-orchestrator`
- `tribunal`
- `remediator`
- `radar`
- `compass`

## Interface Changes
- add `ExecutionContract`, `AdmissibilityDecision`, `ExecutionFrontier`,
  `ResourceClosure`, `SemanticReceipt`, `ValidationMatrix`,
  `ContradictionRecord`, and host-profile aware execution helpers
- add one new program file contract at
  `odylith/radar/source/programs/B-072.execution-waves.v1.json`
- add top-level `odylith program ...` and `odylith wave ...` commands as a
  sidecar authoring surface over the existing execution-wave contract

## Migration/Compatibility
- keep release planning separate from execution-wave planning
- keep execution governance host-general across Codex and Claude Code, then
  layer detected host/model-family nuance additively
- treat the new program/wave CLI as a thin wrapper around the canonical
  `*.execution-waves.v1.json` contract instead of a replacement schema

## Test Strategy
- validate umbrella metadata, execution-wave file integrity, and plan binding
- add focused unit coverage for execution-governance contracts and authoring
  commands
- prove packet-summary and shared runtime-surface carry-through for execution
  governance outcome, frontier, closure, wait state, resume posture, and
  detected host-family posture
- preserve existing execution-wave read-model coverage so Radar and Compass
  keep rendering the same source of truth

## Open Questions
- which external dependency adapters deserve first-class product ownership
  after local commands, Compass/agent-stream state, and GitHub Actions
- how aggressively the execution-governance layer should auto-adapt policy by
  detected host or model family before explicit operator override exists
