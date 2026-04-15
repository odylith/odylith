# Governance Intervention Engine
Last updated: 2026-04-14


Last updated (UTC): 2026-04-14

## Purpose
Governance Intervention Engine is Odylith's shared conversation-observation
runtime. It watches live Codex and Claude session evidence, turns corroborated
governance truth into humane in-flow `Odylith Observation` beats, upgrades
stable governed write opportunities into confirmation-gated
`Odylith Proposal` bundles, and keeps that whole lifecycle auditable
through Compass instead of leaving it as host-local improvisation. It also
owns the live mid-turn surface contract for teaser and explicit intervention
beats so prompt, stop, post-edit, and post-bash hooks do not have to route
through the heavier closeout chatter stack just to speak one truthful line.

## Scope And Non-Goals
### Governance Intervention Engine owns
- The shared cross-host `ObservationEnvelope` intake contract.
- The live mid-turn conversation surface fast path used by Codex and Claude
  hooks, including teaser rendering, low-signal suppression, and host-parity
  shaping.
- Fact selection for `history`, `governance_truth`, `invariant`, `topology`,
  and `capture_opportunity` beats.
- Intervention thresholds for teaser, corroborated observation card, and
  proposal eligibility.
- Duplicate suppression keyed to the active session and prior Compass
  intervention lifecycle events.
- Proposal assembly across Radar, Registry, Atlas, and Casebook, including the
  one-confirmation bundle contract.
- CLI-first apply for supported deterministic governed writes.
- The default intervention voice contract seam, including future
  voice-pack-ready metadata without exposing selectable packs yet.

### Governance Intervention Engine does not own
- Repo grounding, packet compilation, or retrieval widening; that belongs to
  [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md).
- Admissibility or urgency policy by itself; that belongs to
  [Execution Governance](../execution-governance/CURRENT_SPEC.md).
- Human narration policy outside observation and proposal blocks; that belongs
  to [Odylith Chatter](../odylith-chatter/CURRENT_SPEC.md), which stays the
  closeout and broader narration layer.
- Stream audit storage or pending-proposal read models; that belongs to
  [Compass](../compass/CURRENT_SPEC.md).
- Unsafe auto-update flows where no safe CLI-backed helper exists yet.

## Developer Mental Model
- The engine should feel like Odylith quietly joining the conversation at the
  exact right moment, not like a compliance bot interrupting every turn.
- The runtime should make its first decision before touching repo truth:
  classify the prompt, summary, refs, and changed paths into a cheap semantic
  signal profile, then stay silent immediately if there is no governed signal
  worth carrying.
- Distinct causal points on the same governed slice must keep distinct
  intervention keys. Repeating the same governed truth should suppress cleanly;
  shifting to a new non-obvious fact on that slice must stay eligible to
  surface.
- Prompt-only evidence may earn one lightweight teaser sentence. It must not
  jump straight to a rich markdown block or a governed write suggestion.
- Full `Odylith Observation` blocks need corroboration from at least two
  evidence classes among prompt text, assistant summary, changed paths,
  packet or execution truth, or governed artifact matches.
- `Odylith Proposal` is the smallest coherent governed action bundle Odylith
  can honestly carry from the evidence in front of it. It is not a loose pile
  of chores.
- Voice is part of the runtime contract. The shipped default voice must stay
  friendly, delightful, soulful, insightful, simple, clear, accurate,
  precise, and above all human. Templated or mechanical copy is a regression.
- Cross-host shared core is non-negotiable. Codex and Claude adapters may
  differ only in hook envelopes and host response surfaces, never in core fact
  selection, labels, or proposal semantics.
- Cross-lane consistency is also non-negotiable. Detached `source-local`,
  pinned dogfood, and consumer pinned-runtime lanes may carry different
  evidence and refresh posture, but they must not fork the observation or
  proposal product contract.

## Runtime Contract
### Owning modules
- `src/odylith/runtime/intervention_engine/contract.py`
  Canonical dataclasses for observation, facts, candidates, proposals, and the
  shared bundle payload.
- `src/odylith/runtime/intervention_engine/engine.py`
  Shared fact selection, intervention staging, proposal assembly, and
  render-policy emission.
- `src/odylith/runtime/intervention_engine/signal_kernel.py`
  Cheap semantic kernel that scores prompt, summary, target refs, changed
  paths, and session-memory continuity before any heavier repo-truth work.
- `src/odylith/runtime/intervention_engine/moment_runtime.py`
  Dominant-moment selector that scores urgency, novelty, continuity, and
  governance-readiness to choose one earned interjection.
- `src/odylith/runtime/intervention_engine/continuity_runtime.py`
  Cross-phase moment continuity runtime that keeps teaser, Observation, and
  Proposal on one stable session-local identity instead of treating every hook
  as a fresh branded thought.
- `src/odylith/runtime/intervention_engine/voice.py`
  Default brand voice renderer for `Odylith Observation` and
  `Odylith Proposal`.
- `src/odylith/runtime/intervention_engine/conversation_surface.py`
  Shared low-latency live-surface bundle builder and renderer for prompt,
  stop, post-edit, and post-bash host phases.
- `src/odylith/runtime/intervention_engine/host_surface_runtime.py`
  Shared host payload builder that keeps one hidden developer-context bundle
  for continuity while composing the visible checkpoint or stop surface for
  Codex and Claude.
- `src/odylith/runtime/intervention_engine/conversation_runtime.py`
  Shared ambient-signal selection, closeout Assist composition, and
  conversation-bundle assembly for subagent orchestration plus host-adoption
  summaries.
- `src/odylith/runtime/intervention_engine/delivery_runtime.py`
  Shared delivery-signal snapshot reader and Tribunal-context normalization
  for both ambient signaling and closeout truth.
- `src/odylith/runtime/intervention_engine/claim_runtime.py`
  Shared claim-lint enforcement bridge so ambient lines, Assist closeout, and
  supplemental signals use one proof-state safety gate.
- `src/odylith/runtime/intervention_engine/surface_runtime.py`
  Shared host-surface helpers, markdown rendering, and Compass event emission.
- `src/odylith/runtime/intervention_engine/stream_state.py`
  Compass stream reads plus cached derived session-memory and
  pending-proposal state.
- `src/odylith/runtime/intervention_engine/apply.py`
  CLI-first apply and decline handling for supported proposal bundles.
- `src/odylith/runtime/intervention_engine/cli.py`
  Thin `odylith governance intervention-preview` and
  `odylith governance capture-apply` entrypoints.

### Core public types
- `ObservationEnvelope`
  Fixed fields: `host_family`, `session_id`, `turn_phase`, `prompt_excerpt`,
  `assistant_summary`, `changed_paths`, `packet_summary`, `delivery_snapshot`,
  and `active_target_refs`.
- `GovernanceFact`
  Fixed fact classes: `history`, `governance_truth`, `invariant`,
  `topology`, and `capture_opportunity`.
- `InterventionCandidate`
  Shared teaser-or-card payload with key, stage, evidence classes, and
  rendered observation content.
- `CaptureAction`
  Surface-local proposal action for `radar`, `registry`, `atlas`, or
  `casebook`, using deterministic `create`, `update`, `reopen`, `link`, or
  `review_refresh` semantics.
- `CaptureBundle`
  Confirmation-gated proposal payload plus action surfaces, support posture,
  and confirmation text.
- `InterventionBundle`
  One portable payload carrying the observation envelope, selected facts,
  candidate, proposal, render policy, and derived pending state.

### Thresholds And Suppression
- Live intervention is a staged algorithm:
  1. cheap signal kernel on prompt, summary, target refs, changed paths, and
     recent session memory
  2. repo-truth lookup only when that signal kernel earns it
  3. moment selection that scores urgency, novelty, continuity, and
     governance-readiness to choose one dominant interjection instead of
     flattening the first matching fact into stock copy
  4. stable moment identity selection from prompt-rooted identity signatures
     plus governed anchors so prompt-submit, stop-summary, and
     post-edit/post-bash upgrades can evolve the same moment across phases
  5. continuity lookup from cached Compass stream events so the engine knows
     whether the moment already emitted a teaser, Observation, pending
     Proposal, decline, or apply outcome
  6. candidate stage selection from that moment profile so low-signal turns
     stay silent, early real signals stay teaser-only, and corroborated
     high-readiness moments earn one Observation
  7. proposal assembly only after the chosen moment is observation-grade and
     proposal-ready; proposal generation is not an always-on side effect of
     every teaser-worthy signal
- `prompt_submit`
  May emit only teaser text.
- Prompt hooks must not suppress that teaser just because anchor resolution or
  launcher-backed context narrowing is unavailable. Missing anchor context is a
  degraded add-on, not permission to silence a real governed signal.
- `stop_summary`
  May upgrade to a full `Odylith Observation` when corroboration exists, even
  when proposal readiness is still too low to surface `Odylith Proposal` yet.
  In shipped Codex and Claude host lanes, stop-summary is the fallback visible
  surface rather than the primary intervention moment. It should recover a
  missed late Observation and may pair that with a shared closeout Assist line
  when the closeout-side bundle is eligible.
- `post_edit_checkpoint` and `post_bash_checkpoint`
  Are the primary visible intervention lanes. They may upgrade an earned
  observation into a proposal by attaching concrete changed-path evidence and
  governed targets, and should surface the earned Observation/Proposal beat
  visibly at the hook moment instead of trapping it in hidden context only.
- Host payload builders intentionally carry two surfaces at once:
  - hidden developer context (`additionalContext` or
    `hookSpecificOutput.additionalContext`) with the full
    Observation/Proposal/Assist bundle for model continuity
  - visible hook `systemMessage` with the earned Observation/Proposal beat and
    only failure-level governance status when that status materially changes
    the next move
- Success-only governance refresh receipts must not displace an earned visible
  intervention. If a checkpoint already has a real Observation or Proposal,
  the visible surface should stay on that beat and keep routine refresh
  success quiet.
- At most one full `Odylith Observation` card may appear per turn.
- Duplicate full cards for the same causal point in one active session must be
  suppressed from prior Compass event truth.
- Session memory must be cheap enough for prompt hooks and rich enough to
  distinguish a forming beat from a repeated beat. Cached recent-event reads
  and semantic signatures are part of the hot-path contract.
- Derived stream summaries are part of that latency contract too. Session
  memory, pending proposal state, and cross-phase continuity snapshots should
  reuse cached stream signatures instead of reparsing or re-walking the same
  event tail on every live hook.
- Stable continuity identity is distinct from rich reasoning signature. The
  engine may reason from prompt, summary, refs, and changed paths together,
  but the same cross-phase moment must keep one stable key rooted in the
  prompt and governed anchors rather than changing identity every time a new
  hook adds more evidence.
- Exact stable key beats signature fallback. Signature matching exists only as
  a recovery seam when the exact key is unavailable, not as permission to
  merge two distinct governed moments that merely sound similar.
- Observation and Proposal suppression are related but not identical. A later
  hook may suppress a duplicate Observation while still surfacing the first
  eligible Proposal for that same moment.
- Proposal rendering requires explicit user confirmation before any write.
- Proposal apply stays preview-only for update or reopen paths until a safe
  CLI-backed helper exists for that exact surface action.
- Observation and proposal markdown must preserve their multiline structure all
  the way through host rendering, Compass event storage, and pending proposal
  state. Flattening those blocks into one-line log strings is a product
  regression, not a harmless formatting change.
- Session memory must preserve the human conversation, not Odylith's own
  summaries. Intervention lifecycle events therefore carry the originating
  `prompt_excerpt` forward so later stop, post-edit, and post-bash hooks reason
  from the user's actual prompt instead of `Odylith Proposal pending.` or other
  self-generated summaries.
- Stop-time recovery should also preserve the active slice, not only the last
  prompt sentence. Derived changed paths, workstreams, components, and target
  refs recovered from the shared event stream are part of the stop-surface
  contract so closeout and Observation upgrades do not speak from an empty
  context.
- Apply and decline are part of the same continuity chain. Terminal proposal
  events must preserve `moment_kind` and semantic signature so later runtime
  consumers can still understand which governed moment was applied, declined,
  or rendered stale.
- Empty or missing hook session ids must fall back to a stable host-local
  synthetic session token. Intervention runtime may recover recent memory only
  from that resolved session; an empty session id must never widen into
  cross-session prompt or changed-path bleed.
- Proposal apply is all-or-nothing. If any action in the bundle is still
  preview-only or unsupported, `odylith governance capture-apply` must refuse
  the entire bundle instead of writing only the supported subset.
- Bare changed paths with no governed fact, no corroborating semantic signal,
  and no meaningful prompt or assistant evidence must stay silent. Hot-path
  speed is not a license for low-signal filler.

## UX And Voice Contract
- Visible labels are fixed in this release:
  - `**Odylith Observation**`
  - `Odylith Proposal`
- Confirmation phrase is fixed in this release:
  - `apply this proposal`
- The rendered confirmation cue must stay visually quiet.
  It should read like a short trailing sentence such as
  `To apply, say "apply this proposal".`, not a loud code-pill callout.
- `Odylith Observation` should render like `Odylith Assist`: one short labeled
  line, not a mini card. It should surface the non-obvious governed truth and
  one clear implication in one breath.
- That single line must make the interjection explicit. The user should be
  able to tell immediately why Odylith is stepping in now.
- The default voice renderer must vary by selected moment kind such as
  continuation, boundary, guardrail, recovery, or capture. Different governed
  moments must not collapse into the same stock sentence stem.
- Voice variation must stay deterministic across Codex, Claude, and all lanes
  for the same observation envelope. The product should feel alive, not random.
- `Odylith Proposal` must list flat per-surface actions, the governed delta,
  why each target belongs, and one confirmation affordance for the full
  bundle.
- `Odylith Proposal` should render as one short ruled block:
  - opening rule
  - one calm lead line beginning with `Odylith Proposal:`
  - a few short bullets
  - one quiet confirmation sentence
  - closing rule
- Proposal copy should stay plain and compact, not explanatory for its own
  sake. The goal is a quick, confident suggestion, not a second essay.
- The default renderer should feel warm and lucid, not ornamental or robotic.
  Blank-line-separated Markdown sections are preferred over dense one-line log
  formatting.
- Proposal bullets should stay crisp enough to scan in one pass, but rich
  enough that the user can see the governed delta, why the target belongs, and
  whether the whole bundle is preview-only without reading code or raw JSON.
- When maintainers, host guidance, or tests demonstrate Observation or
  Proposal UX to humans, prefer rendered Markdown or plain narrative over
  fenced raw Markdown blocks. Showing the product moment as a code sample is
  acceptable only for debugging the raw source text.
- Demo and fixture copy must stay concrete. Filler marketing lines that do not
  carry real governed meaning are a UX regression even in mockups.
- Compass pending proposal state must carry rich proposal display payloads and
  proposal status, not just terse counters, so downstream shells and future UI
  surfaces can render the same delightful proposal preview without reconstructing
  it from fragments.
- Compass proposal summaries should stay human and semantically useful. Do not
  regress event summaries or pending-state rows back into self-referential
  placeholders such as `Odylith Proposal pending.`
- Voice-pack selection is deferred, but the runtime must expose a clear
  future-ready seam in `render_policy.voice_contract` so later releases can
  tune voice without forking host logic.

## Command Surface
- `odylith governance intervention-preview`
  Build one structured observation and proposal bundle from an
  `ObservationEnvelope`.
- `odylith governance capture-apply`
  Apply or decline one confirmed `Odylith Proposal` payload.

These commands are shared across Codex, Claude, maintainer `source-local`,
pinned dogfood, and consumer pinned-runtime lanes. Host-specific wrappers may
shape envelopes, but they must not invent alternate proposal commands or
parallel payload schemas.

## Proposal Apply Contract
- Radar actions may create or extend workstream truth when a deterministic CLI
  helper exists.
- Registry actions may register or refresh a component dossier when the target
  helper exists.
- Atlas actions may scaffold a diagram or refresh review truth when the target
  helper exists.
- Casebook actions may capture or reopen a bug when the target helper exists.
- Apply emits Compass lifecycle events:
  `capture_applied` or `capture_declined`.
- Apply must refresh only the touched governed surfaces. It must not widen into
  a full-repo sync just to close one proposal.
- Apply must reject stale terminal bundles and preview-only bundles before any
  governed write begins.

## Composition
- [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md) supplies
  bounded packet and anchor truth.
- [Delivery Intelligence](../delivery-intelligence/CURRENT_SPEC.md) supplies
  posture and lane context through `delivery_snapshot`.
- [Execution Governance](../execution-governance/CURRENT_SPEC.md) supplies
  admissibility and urgency signals without taking over voice or rendering.
- [Odylith Chatter](../odylith-chatter/CURRENT_SPEC.md) renders the final
  closeout/persona layer and may consume the carried `intervention_bundle`
  later, but the live mid-turn Observation/Proposal path is intervention-owned
  so host hooks stay fast and consistent.
- [Compass](../compass/CURRENT_SPEC.md) owns the append-only stream events and
  derives pending proposal state from those events.
- [Atlas diagram D-038](../../../../atlas/source/odylith-conversation-observation-and-governed-proposal-flow.mmd)
  is the canonical topology record for this flow.

## What To Change Together
- If the observation envelope fields change, update the dataclass contract,
  host envelope builders, CLI preview path, and cross-host tests together.
- If teaser, observation, or proposal thresholds change, update the core
  engine, voice expectations, and host integration tests together.
- If proposal actions gain new deterministic apply support, update the apply
  runtime, CLI contract, and surface refresh expectations together.
- If the default voice changes, update `voice.py`, Chatter guidance,
  maintainer guidance, and host contracts together.
- If lane semantics change, preserve the shared observation and proposal UX
  across `source-local`, pinned dogfood, and consumer pinned-runtime lanes;
  lane changes may affect evidence inputs, not product labels or tone.

## Validation Playbook
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine_apply.py tests/unit/runtime/test_intervention_engine_performance.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_conversation_surface.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_claude_host_prompt_context.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_claude_host_stop_summary.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-14: Promoted Governance Intervention Engine into a first-class Registry component so Codex and Claude can share one portable conversation observation and governed proposal runtime instead of host-local intervention heuristics. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Shipped the fixed user-facing labels `Odylith Observation` and `Odylith Proposal`, the single-confirmation proposal apply contract, the future-ready voice-pack seam, and Atlas diagram `D-038` to keep runtime, governance, and maintainer guidance aligned. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Hardened the product contract so rich markdown survives the full host and Compass path, duplicate suppression keys stay causal rather than overly coarse, proposal apply is all-or-nothing for CLI-safe bundles, and warm-cache latency stays covered by focused regression tests. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Extended intervention lifecycle events to carry prompt memory and rich pending-proposal display payloads so later hooks keep reasoning from the human conversation and Compass can expose delightful proposal previews without rebuilding them downstream. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Split rich reasoning signature from stable continuity identity, added a cross-phase continuity runtime, and allowed first-time Proposal upgrades to surface without re-announcing a duplicate Observation. This made teaser, Observation, and Proposal feel like one evolving thought instead of three disconnected hook artifacts. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
