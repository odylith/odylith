---
status: queued
idea_id: B-070
title: Benchmark Host-Family Proof Canon and Live Runner Schema Normalization
date: 2026-04-09
priority: P1
commercial_value: 4
product_impact: 4
market_value: 3
impacted_parts: benchmark live-execution payloads, benchmark runner publication schema, proof graphs, benchmark docs, and maintainer proof guidance
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: The shared cross-host runtime and governance contract is now clean enough to close, but the benchmark subsystem still emits Codex-branded canonical fields such as `raw_codex_cli` and `codex_prompt_*` in live execution rows and published reports. Splitting that benchmark-only tail out of `B-069` keeps the broader product contract honest while preserving a bounded follow-up for report schema, graph, and test normalization.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-069
workstream_children:
workstream_depends_on: B-060,B-069
workstream_blocks:
related_diagram_ids: D-024
workstream_reopens:
workstream_reopened_by:
workstream_split_from: B-069
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
The benchmark subsystem still leaks Codex-branded canon into fields that are
supposed to describe the proof host generically. Live execution rows still use
`raw_codex_cli` as the baseline packet source, token accounting still centers
`codex_prompt_*` field names, and benchmark graphs and tests still read those
fields as if they were the canonical shared report contract.

That means the product-wide host separation is now cleaner than the benchmark
report schema that is supposed to prove it.

## Customer
- Primary: maintainers and reviewers who need benchmark reports to tell the
  truth about host-scoped proof without treating Codex naming as the whole
  benchmark contract.
- Secondary: future Claude-proof work that should extend a host-neutral report
  schema instead of translating away old Codex-first field names first.

## Opportunity
If the benchmark subsystem adopts host-neutral canonical fields now, future
proof publication can keep Codex-host-scoped evidence honest while still
describing the harness, prompt cost, and packet source in one reusable schema.

## Proposed Solution
Introduce host-neutral canonical benchmark fields such as
`benchmark_host_family`, `agent_prompt_estimated_tokens`, `runner`, and
`packet_source`, keep the current Codex-branded names as compatibility aliases
for one release, and update benchmark graphs, docs, and tests to prefer the
canonical fields first.

## Scope
- replace benchmark live-runner canonical values like `raw_codex_cli` with
  host-neutral canon such as `raw_host_cli` and `live_host_cli`
- add canonical host-family and prompt-token fields while keeping the current
  Codex-branded report fields as compatibility aliases
- update benchmark graph generation, benchmark docs, and benchmark tests to
  read the canonical fields first
- keep public proof explicitly host-scoped until Claude has measured proof of
  its own

## Non-Goals
- publishing Claude benchmark proof without a fresh matched-host run
- rewriting archived `.odylith` benchmark reports
- weakening Codex-scoped publication claims that are still factually correct

## Risks
- compatibility alias coverage could be incomplete and break historical graph
  or report readers
- public proof tables could become misleading if host-scoped publication and
  host-neutral schema are not kept distinct
- benchmark docs could drift if the schema migration lands without regenerated
  graphs and reviewer guidance

## Dependencies
- `B-069` closed the shared runtime, governance, and UX host-separation work
  and split the remaining benchmark-only schema tail here
- `B-060` already owns active release-proof hardening and remains the nearby
  release context for benchmark publication discipline

## Success Metrics
- live benchmark rows use host-neutral canonical runner and packet-source
  fields
- benchmark reports expose host-neutral token and host-family canon while
  preserving compatibility aliases for one release
- benchmark graphs, tests, and docs read the canonical fields first
- published proof stays explicitly host-scoped

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_live_execution.py tests/unit/runtime/test_odylith_benchmark_graphs.py tests/unit/runtime/test_hygiene.py`
- `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- `git diff --check`

## Rollout
Treat this as the benchmark-only child follow-up to `B-069`. Land the schema
migration behind compatibility aliases, regenerate the benchmark-derived docs
and graphs, then retire the Codex-branded report fields once one compatibility
release has passed.

## Why Now
`B-069` cleaned up the product contract everywhere else. Leaving the benchmark
schema behind would make future host-proof work pay the same translation tax
again.

## Product View
Host neutrality is not complete if the proof layer still talks like the first
host is the product itself.

## Impacted Components
- `benchmark`
- `odylith`

## Interface Changes
- benchmark reports gain host-neutral canonical host-family, runner, and
  prompt-token fields
- benchmark live-execution payloads stop using Codex-branded canonical runner
  labels
- Codex-branded benchmark fields remain readable as compatibility aliases for
  one release

## Migration/Compatibility
- keep `codex_prompt_*`, `raw_codex_cli`, and related Codex-branded benchmark
  fields readable during the migration release
- do not rewrite archived local benchmark reports
- regenerate only current docs, graphs, and checked-in benchmark surfaces

## Test Strategy
- extend benchmark runner and live-execution tests for the canonical fields and
  alias behavior
- update benchmark graph tests to read canonical fields first
- rerun benchmark hygiene and sync proof after the schema change

## Open Questions
- whether to add a dedicated `published_proof_host_family` field in addition to
  the canonical `benchmark_host_family`
- how long the Codex-branded compatibility aliases should remain visible in
  public benchmark payloads
