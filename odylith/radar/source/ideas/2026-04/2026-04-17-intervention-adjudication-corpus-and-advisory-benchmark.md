status: implementation

idea_id: B-108

title: Intervention Adjudication Corpus And Advisory Benchmark

date: 2026-04-17

priority: P0

commercial_value: 4

product_impact: 5

market_value: 4

impacted_parts: intervention adjudication corpus, benchmark reporting, value_engine tests, odylith_on proof story

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Without honest corpus provenance the value engine becomes fake ML and damages trust.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md

execution_model: standard

workstream_type: child

workstream_parent: B-096

workstream_children:

workstream_depends_on: B-106

workstream_blocks:

related_diagram_ids: D-038

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Selector quality cannot be honestly claimed from synthetic or sparse bootstrap cases, but v0.1.11 still needs regression coverage and advisory mechanism metrics.

## Customer
Maintainers deciding whether Odylith-visible signals are precise, useful, low-noise, and worth brand attention.

## Opportunity
Create a governed adjudication corpus with provenance, density gates, deterministic evaluation, and reports that separate advisory selector metrics from odylith_on outcome proof.

## Proposed Solution
Maintain governed corpora and advisory reports that make signal-quality claims
honest. The intervention-value corpus records provenance, adjudicator,
rationale, duplicate groups, expected selections, must-suppress propositions,
visibility expectation, and calibration-counting eligibility. The guidance
behavior corpus is a separate benchmark family for high-risk guidance pressure
cases and validates its own runtime layer contract. The deterministic
guidance-behavior validator also proves the guidance-surface contract across
Codex, Claude, installed skills, command shims, and consumer/pinned-dogfood/
source-local lane instructions so benchmark proof and host guidance do not
split.

## Scope
- Keep synthetic and bootstrap cases useful for regression but excluded from
  publishable calibration quality.
- Report selector metrics as mechanism evidence, not full `odylith_on` outcome
  proof.
- Add the `guidance_behavior` benchmark family, corpus mirror, validator
  command, and runtime-layer validation so guidance behavior proof is
  measurable without provider calls.
- Add guidance-surface validation for host and lane instructions, including
  Codex `spawn_agent`, Claude Task-tool subagents, installed skills, and the
  consumer/dogfood/source-local proof path.
- Keep benchmark isolation aware of both live and bundle corpus mirrors.

## Non-Goals
- Do not publicize precision, recall, or calibration claims from sparse
  synthetic seed cases.
- Do not merge guidance behavior cases into the intervention-value calibration
  corpus; they prove a different contract.

## Risks
- A real report can still mislead if it collapses synthetic regression rows,
  guidance pressure cases, and non-synthetic intervention adjudication into one
  headline metric.

## Dependencies
- B-106 value-engine decisions.
- CB-123 calibration/provenance overclaim guardrail.
- Benchmark taxonomy and isolation contracts.

## Success Metrics
Corpus validation rejects missing provenance, contradictory labels, and synthetic calibration counting; advisory report includes precision, recall, duplicate rate, visibility recall, no-output accuracy, p95 latency, quality_state, and publishable flag; guidance-behavior benchmark reports expose the selected family filter and hard-gate posture at top level for quick release-proof reads.

## Validation
- Corpus validation rejects missing provenance, contradictory labels,
  synthetic calibration counting, stale bundle mirrors, and under-density
  publish attempts.
- `odylith validate guidance-behavior --repo-root . --json` passes and proves
  corpus, benchmark-family, bundle mirror, runtime-layer integration, and
  host/lane guidance-surface alignment.
- `odylith benchmark --profile quick --family guidance_behavior --json`
  selects only the guidance-behavior family and reports hard-gate status
  without creating a separate public proof lane.

## Rollout
- Ship bootstrap/advisory reports in v0.1.11; keep calibration loading disabled
  until non-synthetic density gates pass.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should be brutally honest about signal quality: bootstrap cases catch regressions, real adjudication earns calibration later, and synthetic data never counts toward public precision claims.

## Impacted Components
- `governance-intervention-engine`
- `benchmark`
- `odylith-context-engine`

## Interface Changes
- New governed corpus:
  `odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json`.
- New validation command:
  `odylith validate guidance-behavior`.
- Benchmark taxonomy includes the `guidance_behavior` family.

## Migration/Compatibility
- Guidance behavior corpus mirrors must ship with the source bundle; missing or
  stale mirrors are validation failures.

## Test Strategy
- Test corpus provenance, benchmark family taxonomy, isolation allowlists,
  bundle mirror sync, runtime-layer token checks, and advisory report fields.

## Open Questions
- Publishable calibration remains deferred until the real adjudicated data
  density gates are met.
