status: implementation

idea_id: B-107

title: Host Visibility Integration And Ruler Canonicalization

date: 2026-04-17

priority: P0

commercial_value: 4

product_impact: 5

market_value: 5

impacted_parts: Codex host surfaces, Claude host surfaces, visibility_broker, host_surface_runtime, conversation_surface

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Visible delivery and formatting are the product contract the user is explicitly judging.

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
Codex and Claude can generate intervention payloads that remain hidden, and live blocks can lose their top or bottom Markdown ruler while Assist must remain closeout-owned.

## Customer
Users in live chats who need Odylith Observation, Proposal, Risks, History, and Insight to be visibly readable and consistently formatted.

## Opportunity
Make the visibility broker consume selected value-engine options, prove chat visibility, repair missing live rulers, and keep Assist outside ruled live blocks.

## Proposed Solution
Make the visibility broker consume the selected value-engine options and own
delivery proof for Codex, Claude, manual fallback, prompt/checkpoint replay,
Stop recovery, status probes, and tests. Generated hidden payloads remain
non-success until visible fallback or exact assistant transcript confirmation
proves the user could see the Odylith text.

## Scope
- Separate ledger-visible fallback from strict assistant transcript proof.
- Replay pending hidden, manual-visible, best-effort, and Stop-continuation
  blocks until exact `assistant_chat_confirmed` proof exists.
- Repair missing top/bottom rulers for live Ambient, Observation, and Proposal
  blocks instead of dropping otherwise useful signals.
- Keep `Odylith Assist` closeout-owned and outside the ruled live block.
- Preserve same-block behavior across Codex and Claude while honoring each
  host's actual transport limits.

## Non-Goals
- Do not pretend Codex native desktop apply/exec hooks are covered when the
  exposed hook schema is Bash-only.
- Do not count hidden `systemMessage` or `additionalContext` as chat-visible
  product proof.

## Risks
- Duplicate fallback replay can become noisy if confirmation keys ignore the
  rendered block text or collapse distinct same-label ambient propositions.

## Dependencies
- B-106 selected options and proposition identities.
- Compass intervention stream delivery metadata.
- Host prompt, post-tool, Stop, visible-intervention, and status surfaces.

## Success Metrics
Codex and Claude consume the same selected options; hidden systemMessage/additionalContext never count as proof; Stop recovery replays unseen live blocks before Assist; ruled block tests pass.

## Validation
- Host-visible tests prove hidden payloads do not count as proof, fallback
  output replays until exact assistant confirmation, same-label distinct blocks
  confirm independently, and Assist stays outside live rulers.

## Rollout
- Ship as the v0.1.11 visibility contract for existing sessions via direct
  visible fallback and for fresh sessions via reloaded host guidance/hooks.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should never claim success from hidden hook JSON; earned live blocks render visibly with canonical rulers while Assist stays at the final closeout.

## Impacted Components
- `governance-intervention-engine`
- `compass`
- `odylith-chatter`

## Interface Changes
- Delivery proof states distinguish generated/fallback-ready,
  ledger-visible, pending confirmation, and `assistant_chat_confirmed`.
- Visible replay output is a shared read model consumed by prompt,
  checkpoint, status, manual fallback, and Stop surfaces.

## Migration/Compatibility
- v0.1.11 ledger migration infers legacy visible-family rows from
  `render_surface` and promotes fallback-visible rows once when exact
  assistant transcript proof appears.

## Test Strategy
- Exercise Codex and Claude prompt, post-tool, visible-intervention, status,
  Stop, and transcript-confirmation paths against the same selected block set.

## Open Questions
- The remaining release question is live host reload proof, not core delivery
  semantics.
