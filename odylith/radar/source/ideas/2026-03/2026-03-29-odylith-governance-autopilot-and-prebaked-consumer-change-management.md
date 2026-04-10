---
status: finished
idea_id: B-024
title: Governance Autopilot and Prebaked Consumer Change Management
date: 2026-03-29
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: shared guidance, shared skills, install-managed AGENTS activation, bundled consumer assets, and governance closeout behavior across backlog, Registry, Atlas, Casebook, Compass, and session context
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith already has the governance surfaces, memory layer, and grounded execution stack, but the product still leaves too much of the magical bookkeeping loop implicit. If agents have to remember on their own to search for a workstream, extend or create the right backlog record, suggest or deepen a component, update Atlas, search Casebook, capture bugs, and keep intent plus constraints visible in Compass and session context, then Odylith undersells the very product behavior it was built to provide. Prebaking that loop into the installed guidance, skills, and repo-root activation should make consumer installs materially stronger from the first turn.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-governance-autopilot-and-prebaked-consumer-change-management.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-001, B-010, B-016
workstream_blocks:
related_diagram_ids:
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
Odylith's guidance already says to keep governed surfaces truthful, but it does
not yet express the full governance-autopilot loop as the default operating
contract across consumer, developer, dogfood, and maintainer lanes. The result
is that agents may still treat backlog, plan, component, Atlas, Casebook, and
Compass upkeep as optional follow-up work instead of as part of normal
grounded implementation.

## Customer
- Primary: consumer repos that install Odylith and expect the product to handle
  repo bookkeeping and governed closeout automatically rather than by manual
  operator memory.
- Secondary: Odylith maintainers dogfooding the product in the product repo and
  expecting the same autopilot contract to hold in the product's own
  documentation and skills.

## Opportunity
If Odylith encodes the always-on governance loop directly into shared guidance,
shared skills, and install-managed activation, then every grounded repo task
starts with the same expectations: search existing workstreams, extend rather
than duplicate, create new backlog or plan truth when missing, suggest and
deepen components, update or create Atlas diagrams, search and capture
Casebook bugs, and keep intent, constraints, and validation obligations alive
in session context and Compass.

## Proposed Solution
Strengthen the shared Odylith AGENTS contract, delivery/governance guidance,
context and session guidance, and the supporting shared skills so they all say
the same thing explicitly. Update install-managed consumer bootstrap guidance
and repo-root activation text so fresh consumer installs ship that governance
autopilot behavior by default. Mirror the same contract into bundled consumer
assets so upgrade and repair continue to deliver it automatically.

## Scope
- tighten shared guidance so governance upkeep is part of normal implementation
- make backlog and plan search, extension, creation, lineage, and execution
  wave decisions explicit default behavior
- make component suggestion plus living-spec upkeep explicit default behavior
- make Atlas create-or-update expectations explicit default behavior
- make Casebook search and capture expectations explicit default behavior
- make session and Compass context accumulation explicit default behavior
- update install-managed consumer AGENTS text so the contract ships by default
- update focused install tests for the stronger shipped guidance

## Non-Goals
- changing runtime packet schemas or adding a new hosted memory backend
- introducing autonomous tracked-file mutation without approval
- replacing fail-closed governance judgment with unconditional surface spam

## Risks
- over-specifying the workflow could make agents create noisy governance churn
  instead of grounded updates
- install-managed text could drift from bundled guidance if hard-coded strings
  are not kept aligned
- a vague autopilot contract could encourage duplicate workstreams or weak bug
  capture instead of higher-quality closeout

## Dependencies
- `B-001` established Odylith's self-governing product boundary
- `B-010` established durable judgment memory and memory productization
- `B-016` made install-time agent activation and guidance sync first-class

## Success Metrics
- shared guidance across all lanes explicitly treats backlog, plan, component,
  Atlas, Casebook, Compass, and session upkeep as part of normal grounded work
- shared skills encode the same governance-autopilot loop instead of leaving it
  to operator memory
- fresh consumer installs receive repo-root and `odylith/` guidance that
  already describes the autopilot contract
- install and upgrade tests prove the shipped consumer text contains the
  stronger governance posture

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_agents.py tests/integration/install/test_manager.py`
- `git diff --check`

## Rollout
Land the shared guidance and shared skills first, mirror them into bundled
consumer assets, update install-managed text to match, and prove the contract
through the focused install tests so future consumer installs get the stronger
behavior automatically.

## Why Now
This is the product's most important leverage. Odylith should not require a
human to remember the bookkeeping loop if the whole point is to make grounded
repo change management feel automatic and cumulative.

## Product View
The magical part of Odylith is not only narrower retrieval. It is the feeling
that the repo keeps learning and keeping score: backlog truth stays current,
components get deeper, diagrams stay fresh, bugs stop being rediscovered, and
context plus constraints compound instead of resetting every turn.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `subagent-orchestrator`
- `radar`
- `registry`
- `atlas`
- `casebook`
- `compass`

## Interface Changes
- consumer and product guidance now explicitly default to governance-autopilot
  closeout
- install-managed AGENTS activation text now ships that same contract in fresh
  consumer repos
- shared skills now encode the same search, extend, suggest, create, capture,
  and sync loop

## Migration/Compatibility
- no data migration required
- changes are additive to the current install contract
- upgrade and repair should naturally pick up the stronger managed guidance

## Test Strategy
- update focused install guidance tests for the stronger managed block and
  bootstrap guidance
- validate bundle and shipped guidance through the install integration path

## Open Questions
- should a later runtime slice expose an explicit governance-autopilot packet
  or command instead of relying on guidance and skills alone
