---
status: finished
idea_id: B-020
title: Benchmark Integrity, Conservative Multi-Profile Proof, and README Hardening
date: 2026-03-29
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: benchmark runner authenticity contract, cache-profile proof lane, published benchmark summary, benchmark component dossier, benchmark Atlas proof topology, benchmark graphs, README benchmark narrative, and maintainer release proof discipline
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith's benchmark numbers are now strong enough that the main risk is no longer just performance headroom but credibility drift. If the published report still centers the easiest eligible profile or weakly explains its methodology, the product can accidentally overstate its value. Tightening the benchmark into a conservative multi-profile proof lane improves trust, makes README claims harder to game, and gives the next release a sturdier benchmark contract.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-benchmark-integrity-conservative-multi-profile-proof-and-readme-hardening.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-009, B-019
workstream_blocks:
related_diagram_ids: D-024
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
Odylith's benchmark lane is green, but the published benchmark story is still
too easy to misread or over-trust. The runner can execute more than one cache
profile, yet the public report and README still center a single primary
profile. That leaves a credibility gap: Odylith could look stronger in the
published snapshot than it really is under a tougher warm-plus-cold read of the
same Codex corpus.

## Customer
- Primary: Odylith maintainers and evaluators who need the benchmark to be
  authentic, conservative, and hard to game.
- Secondary: Odylith consumers deciding whether the product genuinely makes
  agentic coding smarter, faster, cheaper, and more reliable than Codex alone.

## Opportunity
If Odylith publishes a conservative multi-profile benchmark summary and states
the methodology more clearly, the benchmark becomes materially more trustworthy.
That turns README proof from a nice scorecard into a stronger product claim
about real agentic coding improvement.

## Proposed Solution
Harden the benchmark runner so the default full benchmark lane exercises both
warm and cold cache profiles, computes a conservative published summary across
those profiles, carries explicit robustness metadata, and only uses that
conservative proof for the public README tables and maintained SVG graphs.

## Scope
- make the default benchmark lane cover both warm and cold cache profiles
- add a conservative published summary derived across the selected cache
  profiles
- promote benchmark into a first-class Registry component with a maintained
  component spec and forensic sidecar
- add Atlas topology proof for the benchmark publication lane so benchmark
  methodology is diagrammed and traceable like the rest of the product
- gate the public benchmark status on the stronger multi-profile proof
- update the benchmark graphs to render from the conservative published view
- tighten the README benchmark narrative so the methodology and limits are clear
- add targeted regression tests for the stronger benchmark contract

## Non-Goals
- redesigning the benchmark corpus families
- weakening the current correctness or validation gates
- introducing hosted eval infrastructure

## Risks
- a stricter published benchmark lane may make Odylith's public numbers look
  worse than the current warm-only snapshot
- multi-profile runs may increase local benchmark time
- conservative aggregation could become confusing if the README does not explain
  what is being published

## Dependencies
- `B-009` established the benchmark corpus truth and parity gate
- `B-019` improved the current frontier but still published from a single
  primary cache profile

## Success Metrics
- the default benchmark report now includes warm and cold cache profiles
- the published comparison is conservative across the selected cache profiles
- Registry tracks Benchmark as a first-class product component with an explicit
  spec, path ownership, workstreams, and diagram linkage
- Atlas carries a maintained benchmark proof diagram linked to the active
  benchmark workstream and plan
- README benchmark numbers and graphs are driven from the conservative view
- required-path recall, validation success, and critical correctness signals
  stay non-regressive under the stronger proof lane

## Validation
- `odylith benchmark --repo-root .`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py tests/unit/test_cli.py`
- `odylith validate component-registry --repo-root .`
- `odylith atlas render --repo-root . --check-only`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_render_mermaid_catalog.py`
- `git diff --check`

## Rollout
Land the benchmark runner hardening first, rerun the full Codex corpus with the
stronger default proof lane, then refresh the README and graph assets from the
new conservative report in the same slice.

## Why Now
Odylith's benchmark delta is finally strong enough that the next failure mode is
credibility, not just performance. The product should get ahead of that and
publish the harder proof lane now.

## Product View
If Odylith claims to make agentic coding materially better, the published
benchmark should be the hardest honest local proof we can stand behind, not the
easiest green snapshot.

## Impacted Components
- `benchmark`
- `odylith`
- `odylith-context-engine`
- `subagent-orchestrator`

## Interface Changes
- `odylith benchmark` now defaults to a stronger multi-profile proof lane
- Registry now tracks Benchmark as a first-class component with its own spec and
  forensic dossier
- Atlas now carries a dedicated benchmark proof-and-publication diagram
- benchmark reports expose a conservative published summary for README use
- README benchmark wording becomes more explicit about methodology and limits

## Migration/Compatibility
- no consumer repo migration required
- existing history reports remain readable
- benchmark output adds fields but keeps the existing primary comparison for
  backward-compatible inspection

## Test Strategy
- add regression coverage for multi-profile latest-report eligibility and
  conservative aggregation
- add graph coverage for the conservative published view
- rerun the benchmark lane and the focused benchmark/unit CLI suites

## Open Questions
- should a later slice add multi-run variance reporting on top of the new
  warm-plus-cold conservative lane

## Outcome
- Benchmark is now a first-class Registry component with an explicit spec,
  forensic sidecar, workstream mapping, and Atlas coverage
- `odylith benchmark` defaults to warm-plus-cold conservative publication and
  the published README or graph assets now derive from that harder proof lane
- B-009, B-019, and B-020 now all point at one shared benchmark proof diagram
