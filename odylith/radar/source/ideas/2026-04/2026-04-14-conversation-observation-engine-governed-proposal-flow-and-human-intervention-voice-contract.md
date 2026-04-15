status: implementation

idea_id: B-096

title: Conversation observation engine, governed proposal flow, and human intervention voice contract

date: 2026-04-14

priority: P1

commercial_value: 3

product_impact: 5

market_value: 5

impacted_parts: runtime,governance,ux

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Odylith either earns trust inside the conversation or it does not. A humane, timely observation and governed proposal experience is core product behavior, not garnish, and it must land as one shared cross-host contract instead of per-host improvisation.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on:

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
Odylith already knows a lot during a live session, but too much of that truth
still stays trapped inside packets, surface indices, or maintainer intuition.
The current experience is missing a first-class way to step into the
conversation at the right moment with historical facts, governance truths,
invariants, and topology that genuinely sharpen the next move.

That missing layer creates two product failures at once:
- the conversation loses timely governed intelligence exactly when it would
  help most
- the governance record only gets updated later, if someone remembers

If Odylith intervenes too early, too often, or in a robotic voice, the brand
loses. If it stays silent, the governance truth decays. This slice exists to
solve that tension directly.

## Customer
- Primary: Odylith operators and maintainers who want the product to feel
  mind-opening and trustworthy during live work, not merely after the fact.
- Secondary: downstream consumer-repo users who should be able to benefit from
  the same humane observation and proposal flow once the runtime ships.

## Opportunity
If Odylith can notice the non-obvious governed fact in the middle of a turn,
surface it in a warm human markdown block, and then offer one coherent
confirmation-gated proposal for Radar, Registry, Atlas, and Casebook truth,
the governance loop becomes a living companion to the work instead of delayed
paperwork.

This turns governance from "remember to document later" into "Odylith quietly
helps keep the truth clean while the evidence is still warm."

## Proposed Solution
Ship a first-class shared runtime package under
`src/odylith/runtime/intervention_engine/` and wire it into Codex and Claude
host observation points. The engine should:
- collect one bounded observation envelope from prompt, stop-summary, and
  post-edit or post-bash checkpoints
- select corroborated governance facts from history, invariants, topology,
  existing governed truth, and capture opportunity
- render one rich `**Odylith Observation**` block when the signal is earned
- assemble one confirmation-gated `**Odylith Proposal**` bundle when the
  governed targets are concrete
- write proposal lifecycle events into Compass and derive pending proposal
  state there instead of introducing a shadow store
- carry the originating prompt excerpt and rich proposal display payload through
  that lifecycle so later hooks and downstream surfaces keep reasoning from the
  human conversation instead of Odylith's own pending-status summaries

## Scope
- Shared contracts for observation envelopes, governance facts, intervention
  candidates, capture actions, capture bundles, and the final intervention
  bundle.
- Cross-host runtime integration for Codex and Claude with one shared core.
- Lane-safe behavior across detached `source-local`, pinned dogfood, and
  consumer pinned-runtime posture.
- CLI-first preview and apply flows for supported governed writes.
- Registry, Atlas, Radar, Compass, and maintainer guidance updates that make
  the observation/proposal UX part of governed product truth.

## Non-Goals
- User-selectable voice packs in this release.
- Per-surface approval flows instead of one bundle confirmation.
- Wide repo search purely to make interventions sound smarter.
- Unsafe automation for update or reopen paths that still lack a safe
  CLI-backed helper.
- Turning Odylith into a constant interrupting copilot.

## Risks
- Great facts delivered in stiff or repetitive copy will still feel like a
  product miss.
- Host-specific drift could reintroduce different labels, thresholds, or
  voices on Codex versus Claude.
- Proposal apply could overreach if it attempts update or reopen writes before
  the correct helper exists.
- The feature can become noisy if duplicate suppression and one-card-per-turn
  rules weaken.
- Later stop, post-edit, or post-bash hooks can turn self-referential and cheap
  if they start using prior `Odylith Proposal pending.` summaries as prompt
  truth instead of the user's actual conversation.

## Dependencies
- Shared packet, delivery, and execution-governance posture from the current
  runtime stack.
- Compass agent-stream lifecycle events for auditability and dedupe.
- Existing deterministic CLI helpers for Radar, Registry, Atlas, and Casebook
  create paths.

## Success Metrics
- Codex and Claude produce the same structured observation and proposal bundle
  for the same evidence.
- Prompt-only evidence produces at most a teaser.
- Corroborated evidence can produce one `Odylith Observation`.
- Stable governed targets can produce one `Odylith Proposal`.
- The markdown feels helpful, warm, simple, and human instead of templated or
  mechanical.
- Proposal lifecycle state is visible in Compass without a second truth store.
- Later hooks keep the original prompt context alive across teaser,
  observation, proposal, apply, and decline phases.
- Pending proposal state carries enough rich markdown and status payload for
  downstream surfaces to render the same delightful Proposal UX without
  rebuilding it from summary strings.

## Validation
- Focused runtime tests for the shared engine and both host integrations pass.
- CLI coverage for preview and apply stays green.
- Radar, Registry, Atlas, and plan traceability validators pass on the touched
  slice.
- Atlas diagram `D-038` renders and matches the shipped topology.

## Rollout
1. Land the shared runtime and host wiring in detached `source-local`.
2. Bind the UX and voice contract into Registry, Atlas, Radar, and maintainer
   guidance.
3. Ship through pinned dogfood with the same Observation/Proposal labels and
   voice.
4. Let consumer repos receive the same experience on upgrade without a lane
   fork.

## Why Now
The conversation experience is now the product. If Odylith only becomes
impressive after the work is over, it leaves its strongest possible moment on
the table.

## Product View
Odylith should feel like a sharp, warm collaborator who remembers the truth,
not a governance clerk. Observation and proposal UX is therefore a core brand
surface, and the brand contract must be governed as rigorously as the runtime.

## Impacted Components
- `governance-intervention-engine`
- `odylith-chatter`
- `compass`
- `execution-governance`

## Interface Changes
- New shared `ObservationEnvelope`, `GovernanceFact`,
  `InterventionCandidate`, `CaptureAction`, `CaptureBundle`, and
  `InterventionBundle` runtime contracts.
- New CLI commands:
  - `odylith governance intervention-preview`
  - `odylith governance capture-apply`
- New Compass stream events:
  - `intervention_teaser`
  - `intervention_card`
  - `capture_proposed`
  - `capture_applied`
  - `capture_declined`

## Migration/Compatibility
- Cross-host shared core is mandatory in v1.
- Codex and Claude host wrappers may differ in hook envelopes only.
- Consumer repos receive the feature via shipped runtime upgrade; no separate
  consumer-only UX fork is allowed.

## Test Strategy
- Unit-test teaser, observation, proposal, dedupe, and apply behavior.
- Assert cross-host equality and cross-lane stability.
- Keep host-surface tests proving that prompt, stop, and edit-checkpoint
  upgrades happen in the right phase without spamming branded blocks.
- Keep regression tests proving prompt memory survives the full intervention
  lifecycle and that richer pending-proposal payloads stay within hot-path
  latency budgets.

## Open Questions
- Which update and reopen helper paths should be promoted from preview-only to
  apply-safe next?
- Which future voice-pack customization surface is worth shipping after the
  default brand voice proves itself in real sessions?
