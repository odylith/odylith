status: finished

idea_id: B-031

title: First-Turn Bootstrap and Short-Form Grounding Commands

date: 2026-03-30

priority: P0

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: top-level CLI grounding entrypoints, repo-root AGENTS activation, shared and bundled guidance, consumer-safe skills, install/on/off messaging, and first-turn operator UX

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Odylith's retrieval, routing, and install contracts are strong enough now that the remaining product loss is avoidable operator friction. Codex can still miss Odylith because the first useful grounding verbs live behind `context-engine` and the repo guidance does not point to one obvious first-turn command. Tightening that path should raise adoption and reduce zero-value repo scans without changing the underlying runtime model.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-015, B-016, B-027

workstream_blocks:

related_diagram_ids: D-002,D-018,D-020

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by: B-069

execution_model: standard

## Historical Note
This slice remains the factual record of the first short-form grounding and
conversation-contract wave. Treat Codex-default first-turn language here as
historical. `B-069` now owns the current cross-host bootstrap and shared
conversation contract.

## Problem
Odylith already has the right grounding packets, but the operator path is still
too insiderish. A new turn still asks Codex to know that the first useful
commands live under `odylith context-engine ...`, while install/on guidance
points at Odylith-first behavior in prose more than in one concrete command.
That makes the product easier to bypass than it should be.

## Customer
- Primary: operators in consumer repos who expect Odylith install or repo
  activation to make Odylith the obvious first-turn workflow on the current
  host.
- Secondary: Odylith maintainers dogfooding in the product repo and wanting the
  same short-form bootstrap path instead of teaching the nested command tree by
  memory.

## Opportunity
If Odylith exposes one short top-level bootstrap path and keeps AGENTS, skills,
help text, and install guidance aligned around it, then the current host can
start from Odylith more consistently without extra product knowledge. That should improve
first-turn grounding, reduce ad hoc repo scans, and make the product feel more
opinionated immediately after install.

## Proposed Solution
Add first-class short-form top-level grounding commands backed by the existing
Context Engine, starting with `odylith bootstrap` and related top-level
grounding verbs, then tighten repo-root managed AGENTS, shared and bundled
skills, and install/on/off quickstart messaging so they all point to the same
first-turn contract and the same explicit fallback contract when Odylith is
intentionally disabled.

Expand the same workstream into Odylith's ambient conversation contract:
mid-task narration stays task-first and human, Odylith-grounded facts get woven
into ordinary progress updates by default, and explicit `Odylith Insight:`,
`Odylith History:`, or `Odylith Risks:` labels only appear when the signal is
sharp enough to earn the interruption. Final closeout keeps one optional
`Odylith Assist:` line with linked updated governance ids inline, plus at most
one supplemental closeout line when the evidence is strong enough and the
assist line is actually present.

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
- grow `odylith-chatter` from a closeout-only note into a benchmark-safe
  structured conversation bundle with ambient `insight`, `history`, and `risks`
  candidates plus a post-execution closeout bundle
- let those ambient chatter beats consume precomputed Tribunal-backed delivery
  signals when that stronger diagnosis is already available in packet or
  surface truth, without triggering live Tribunal work during narration
- normalize explicit and cached Tribunal-backed chatter payloads before
  narration so malformed packet truth degrades quietly instead of leaking raw
  structure into the voice
- keep explicit Odylith-by-name narration rare, earned, and non-templated
- make final closeout name the governance artifacts actually updated, using
  canonical linked ids such as `B-###`, `CB-###`, `D-###`, and component ids
- only allow a supplemental closeout `Odylith Risks:`, `Odylith Insight:`, or
  `Odylith History:` line when an `Odylith Assist:` line is also present

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
- ambient chatter could turn into branded filler if the runtime emits canned
  prose instead of structured facts and suppression rules
- closeout artifact links could lie if they are derived from broad repo scans
  instead of final changed paths and already-built packet truth
- Tribunal-aware chatter could hurt latency or benchmark discipline if it
  starts rebuilding delivery intelligence or invoking Tribunal on demand
- malformed or partial Tribunal-backed packet context could leak awkward raw
  shapes into the voice if narration consumes it without normalization

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
- normal progress updates stay task-first and human while Odylith-grounded
  facts get woven into the conversation when they materially change the next
  move
- explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels
  stay rare, high-signal, and never pile up in one moment
- any end-of-work Odylith branding stays optional, prefers bold
  `**Odylith Assist:**` when Markdown is available, leads with the user win,
  links updated governance ids inline, and shows the factual edge against
  `odylith_off` or the broader unguided path
- shared orchestration runtime emits one structured conversation bundle so
  ambient signals and closeout wording come from one canonical contract instead
  of lane-by-lane improvisation
- ambient `Odylith Insight:`, `Odylith History:`, and `Odylith Risks:` beats
  can consume precomputed Tribunal-backed scope, case, and systemic-brief
  truth when it is already present, without widening benchmark required paths
  or adding live Tribunal execution
- malformed explicit or cached Tribunal-backed chatter payloads degrade
  quietly to silence or lighter heuristics instead of leaking raw structure or
  character-split noise into narration
- a supplemental closeout `Odylith Risks:`, `Odylith Insight:`, or
  `Odylith History:` line only appears when `Odylith Assist:` is also present
- benchmark lanes keep this as metadata-only; the richer conversation contract
  does not widen required paths, hot-path docs, or validation commands
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
- Landed on 2026-04-07 and closed into `odylith/technical-plans/done/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md`.
- Shared-only first turns now keep a bounded grounded slice or prompt-derived
  anchor instead of collapsing straight to degraded-empty fallback when Odylith
  can still narrow locally.
- Shared orchestration runtime now attaches one canonical
  `decision.odylith_adoption.closeout_assist` candidate so Odylith closeout
  branding is deterministic, evidence-backed, and easy to suppress when no
  real user-facing delta exists.
- Ambient conversation intelligence now belongs to the same owning workstream:
  task-first commentary stays the default, explicit `Odylith Insight:`,
  `Odylith History:`, and `Odylith Risks:` beats are reserved for high-signal
  moments, and closeout naming moves to capitalized `Odylith Assist:` with
  linked updated governance ids inline.
- Ambient chatter now also consumes precomputed Tribunal-backed delivery truth
  when governed anchors exist, so `Insight`, `History`, and `Risks` can ride
  stronger scenario, case, and systemic-brief signals without invoking live
  Tribunal work or widening benchmark proof lanes.
- Deep-dive hardening now normalizes explicit and cached Tribunal-fed chatter
  payloads before narration, suppresses assist-less supplemental closeout
  lines, and strips one duplicated proof sentence from the managed guidance
  contract.
