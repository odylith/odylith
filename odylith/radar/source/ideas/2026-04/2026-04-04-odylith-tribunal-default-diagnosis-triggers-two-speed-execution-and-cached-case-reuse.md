---
status: queued
idea_id: B-047
title: Tribunal Default Diagnosis Triggers, Two-Speed Execution, and Cached Case Reuse
date: 2026-04-04
priority: P1
commercial_value: 4
product_impact: 5
market_value: 4
impacted_parts: Tribunal invocation seams, validation-failure diagnosis, unsafe-closeout review, ownership and evidence-conflict handling, delivery-intelligence reasoning refresh, Remediator packet handoff, and Tribunal cache and provider-gate efficiency
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Tribunal is already one of Odylith's strongest diagnosis engines, but it still shows up mostly as a sync or surface-side consequence instead of the default layer when work falls off the clear path. Expanding Tribunal to the right ambiguity seams while preserving a fast deterministic lane, evidence-fingerprint cache reuse, and narrow provider focus should increase product leverage without turning diagnosis into a blanket latency tax.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on:
workstream_blocks:
related_diagram_ids: D-005,D-007,D-010,D-011
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
Tribunal is powerful, but Odylith still uses it too narrowly. Today it is
most visible through `odylith sync`, delivery-intelligence refresh, and
evaluation paths. That leaves several high-value diagnosis seams underpowered:

- failed validation
- unsafe closeout
- ownership ambiguity
- conflicting cross-surface evidence
- bounded recovery entry

If Odylith wants Tribunal to be a real product advantage, it should reach for
it whenever the agent is no longer on a clear path instead of treating it as a
mostly downstream shell artifact.

The risk is the opposite extreme: if Tribunal runs everywhere, it becomes
latency, cost, and cognitive noise on clear-path work that does not need a
multi-actor diagnosis pass.

## Customer
- Primary: Odylith operators and maintainers who want stronger diagnosis and
  recovery behavior exactly when the agent becomes uncertain, blocked, or at
  risk of confidently doing the wrong thing.
- Secondary: Odylith reviewers who need Tribunal to feel like a real operating
  layer in the product, not just a benchmark or shell-story feature.

## Opportunity
If Odylith makes Tribunal the default diagnosis layer for unclear-path work,
then failure handling, closeout, and conflict resolution become more grounded
and less ad hoc. If Odylith also keeps a fast deterministic lane plus cached
case reuse, it can do that without slowing the happy path or multiplying
provider waits.

## Proposed Solution
Define one explicit Tribunal trigger contract for the product:

- run Tribunal by default when work is no longer on a clear path
- do not run deep Tribunal on obvious clear-path edits or low-risk first turns

Implement Tribunal as a two-speed system:

- fast deterministic Tribunal for default diagnosis seams, shell-safe refresh,
  and cheap local case formation
- deep Tribunal for top-ranked cases, explicit recovery flows, and focused
  evaluation or benchmark paths where richer reasoning earns its keep

Carry that contract through the main invocation points:

- failed validation and regression diagnosis
- unsafe closeout and proof-insufficient completion
- contested ownership or authority reads
- conflicting Radar / Registry / Atlas / Compass posture
- Remediator entry and bounded correction packets

Keep the efficiency model explicit too:

- selection remains capped to the most relevant live-actionable non-clear-path
  scopes
- unchanged evidence reuses cached cases by evidence fingerprint and
  actor-policy version
- provider enrichment stays narrow, optional, and degrade-once-per-run when the
  provider is unhealthy

## Scope
- map the product's highest-value Tribunal invocation seams and decide which
  ones are synchronous, asynchronous, or surface-only
- add explicit trigger logic for failed validation, unsafe closeout, and
  ownership or evidence conflict
- preserve a fast deterministic Tribunal lane for routine diagnosis paths
- keep deep/provider Tribunal limited to focused cases where it materially adds
  value
- extend payload and surface metadata so Odylith can show why Tribunal ran and
  which reasoning lane was used
- ensure Remediator packets and governed surface outputs stay aligned with the
  broader trigger contract

## Non-Goals
- running Tribunal on every first turn
- turning every dashboard refresh into a deep Tribunal pass
- replacing Context Engine grounding with Tribunal
- weakening the current cache, cap, and provider guardrails

## Risks
- over-triggering Tribunal on weak signals could slow the product and reduce
  trust in diagnosis quality
- broadening invocation points could blur the boundary between Delivery
  Intelligence, Tribunal, and Remediator if ownership stays implicit
- cache invalidation bugs could preserve stale diagnoses after evidence shifts
- deep/provider Tribunal could leak back onto hot paths if the trigger contract
  is not explicit

## Dependencies
- no hard queued-workstream dependency; this should build on the current
  Tribunal and delivery-intelligence baseline already in the product
- `B-046` is adjacent proof work, but benchmark isolation should not block
  productizing better Tribunal invocation behavior

## Success Metrics
- failed validation, unsafe-closeout, and contested-ownership flows can open a
  Tribunal case without manual forcing
- clear-path work avoids deep Tribunal overhead by default
- unchanged evidence reuses cached Tribunal cases instead of recomputing them
- provider failure degrades one run coherently instead of stalling case after
  case
- Odylith surfaces can explain which cases came from deterministic versus deep
  Tribunal paths

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_tribunal_engine.py tests/unit/runtime/test_delivery_intelligence_engine.py tests/unit/runtime/test_sync_workstream_artifacts.py`
- scenario tests for failed-validation, unsafe-closeout, and ownership-conflict
  trigger paths
- `./.odylith/bin/odylith validate backlog-contract --repo-root .`
- `git diff --check`

## Rollout
Land the trigger map and deterministic fast lane first, then add explicit deep
Tribunal paths where recovery and diagnosis quality matter most, and only then
widen shell or agent-facing invocation surfaces around that stable contract.

## Why Now
Odylith now names Tribunal directly in the product story. The runtime should
start behaving like Tribunal is a first-class diagnosis advantage instead of
mostly a downstream sync artifact.

## Product View
If Tribunal is one of Odylith's real strengths, Odylith should reach for it
whenever the agent is no longer on a clear path. But that should feel like
disciplined diagnosis, not a universal tax.

## Impacted Components
- `tribunal`
- `delivery-intelligence`
- `remediator`
- `compass`
- `radar`

## Interface Changes
- Tribunal payloads and surface rows may gain invocation-lane or trigger-reason
  metadata
- Odylith may expose clearer distinctions between deterministic Tribunal and
  deeper explicit Tribunal runs
- failure and closeout flows may surface one explicit diagnosis handoff instead
  of generic fallback language

## Migration/Compatibility
- no consumer migration required
- the change is additive to Tribunal invocation behavior and should preserve
  current deterministic fallback and cache rules
- old Tribunal payloads and surface rows should remain readable when the new
  trigger metadata is absent

## Test Strategy
- add trigger-path tests that prove clear-path work does not invoke the wrong
  Tribunal lane
- add cache-reuse tests around evidence-fingerprint stability and invalidation
- add recovery-path tests that prove Remediator still receives one bounded
  packet per adjudicated case
- add delivery-intelligence tests that keep sync and shell refresh bounded

## Open Questions
- which validator failures should create a Tribunal case immediately versus
  after the broader refresh cycle
- whether unsafe-closeout gating should depend only on scenario/risk or also on
  explicit Tribunal confidence thresholds
- whether Odylith needs an explicit operator-facing "run Tribunal on this
  scope" path in addition to automatic triggers
