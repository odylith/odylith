---
status: implementation
idea_id: B-031
title: Odylith First-Turn Bootstrap and Short-Form Grounding Commands
date: 2026-03-30
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: top-level CLI grounding entrypoints, repo-root AGENTS activation, shared and bundled guidance, consumer-safe skills, install/on/off messaging, and first-turn operator UX
sizing: M
complexity: Medium
ordering_score: 100
ordering_rationale: Odylith's retrieval, routing, and install contracts are strong enough now that the remaining product loss is avoidable operator friction. Codex can still miss Odylith because the first useful grounding verbs live behind `context-engine` and the repo guidance does not point to one obvious first-turn command. Tightening that path should raise adoption and reduce zero-value repo scans without changing the underlying runtime model.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-015, B-016, B-027
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
Odylith already has the right grounding packets, but the operator path is still
too insiderish. A new turn still asks Codex to know that the first useful
commands live under `odylith context-engine ...`, while install/on guidance
points at Odylith-first behavior in prose more than in one concrete command.
That makes the product easier to bypass than it should be.

## Customer
- Primary: Codex users in consumer repos who expect Odylith install or repo
  activation to make Odylith the obvious first-turn workflow.
- Secondary: Odylith maintainers dogfooding in the product repo and wanting the
  same short-form bootstrap path instead of teaching the nested command tree by
  memory.

## Opportunity
If Odylith exposes one short top-level bootstrap path and keeps AGENTS, skills,
help text, and install guidance aligned around it, then Codex can start from
Odylith more consistently without extra product knowledge. That should improve
first-turn grounding, reduce ad hoc repo scans, and make the product feel more
opinionated immediately after install.

## Proposed Solution
Add first-class short-form top-level grounding commands backed by the existing
Context Engine, starting with `odylith bootstrap` and related top-level
grounding verbs, then tighten repo-root managed AGENTS, shared and bundled
skills, and install/on/off quickstart messaging so they all point to the same
first-turn contract and the same explicit fallback contract when Odylith is
intentionally disabled.

## Scope
- expose top-level short-form grounding entrypoints for the existing Context
  Engine bootstrap and narrowing flow
- make repo-root managed AGENTS text name one obvious first-turn command
- tighten consumer AGENTS so substantive work fails closed without Odylith
  grounding, keeps a concrete packet/workstream in scope, and allows
  background grounding without a fixed visible commentary prefix
- update shared and bundled skills plus guidance to prefer the short-form
  commands
- tighten install/on/off operator messaging so the first useful command and the
  explicit fallback behavior are visible without reading deep docs
- keep the short-form commands backed by the same runtime, transport, and
  fail-closed widening behavior as `odylith context-engine`

## Non-Goals
- changing the underlying Context Engine selection or daemon logic
- forcing automatic packet reads at shell startup
- redesigning the broader shell onboarding surface in this slice

## Risks
- adding short-form aliases could drift from the canonical Context Engine
  behavior if they fork argument handling
- install/help copy could overpromise a bootstrap command that still needs too
  much operator tuning to be useful
- source-owned and bundled guidance could drift again if only one tree is
  updated

## Dependencies
- `B-015` established grounded delegation defaults worth making easier to use
- `B-016` strengthened install-time AGENTS and skills activation
- `B-027` clarified the runtime, write, and validation boundary that these new
  entrypoints must preserve

## Success Metrics
- `odylith --help` shows a short first-turn grounding path without requiring
  the operator to discover `context-engine` first
- repo-root managed AGENTS text gives one explicit first-turn Odylith command
- consumer AGENTS guidance keeps Odylith grounding mandatory for substantive
  repo scan or edits without forcing a fixed visible commentary prefix
- any end-of-work Odylith branding stays optional, prefers bold
  `**Odylith assist:**` when Markdown is available, leads with the user win,
  and shows the factual edge against `odylith_off` or the broader unguided
  path
- shared orchestration runtime emits one deterministic closeout-assist
  candidate so lanes do not improvise their own branded proof lines
- bundled skills and source-owned skills use the same short-form commands
- install/on/off messaging points operators at the same first-turn grounding
  path and explicit fallback behavior
- focused CLI and install guidance tests prove the alias and activation
  contracts together

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py tests/unit/install/test_agents.py tests/integration/install/test_manager.py`
- `git diff --check`

## Rollout
Ship as a product-contract tightening slice. Keep `odylith context-engine` as
the full explicit operator namespace, but make the first-turn happy path short
and visible enough that Codex can use it without insider memory.

## Why Now
Odylith is already far enough along that the remaining miss is productization,
not capability. Leaving the first useful command hidden behind a nested runtime
namespace weakens the exact adoption story the product is trying to prove.

## Product View
Odylith should not require a maintainer to remember the command tree in order
to use Odylith first. The product should hand Codex one obvious first move.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `odylith-chatter`
- `subagent-orchestrator`
- `subagent-router`

## Interface Changes
- Odylith gains short-form top-level grounding commands backed by the existing
  Context Engine
- repo-root AGENTS activation now names an explicit first-turn bootstrap path
- `odylith off` now reads explicitly as a valid fall-back-to-default-agent
  posture while leaving Odylith installed
- source-owned and bundled skills shift to the short-form command examples

## Migration/Compatibility
- no data migration required
- existing `odylith context-engine ...` commands remain supported
- existing installs gain the new guidance through upgrade and repair

## Test Strategy
- add focused CLI dispatch coverage for the new short-form commands
- keep managed AGENTS coverage on the stronger first-turn activation text
- keep consumer install coverage on the synced guidance contract

## Open Questions
- whether a later slice should make `odylith bootstrap` smarter about the
  right working-tree scope when a repo is dirty but the session claim is empty

## Outcome
- Bound to `B-031`; implementation in progress.
- Shared-only first turns now keep a bounded grounded slice or prompt-derived
  anchor instead of collapsing straight to degraded-empty fallback when Odylith
  can still narrow locally.
- Shared orchestration runtime now attaches one canonical
  `decision.odylith_adoption.closeout_assist` candidate so final-only Odylith
  branding is deterministic, evidence-backed, and easy to suppress when no
  real user-facing delta exists.
