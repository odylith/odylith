# Governance Intervention Engine

## Adaptive Agent Operating Character Contract
- Governance Intervention Engine owns live Voice. Character decisions can
  become visible only when they create immediate user value: concise nudges
  need a recovery action, Observations need useful evidence, Proposals need a
  bounded next move, and passing checks stay silent.
- Character supplies evidence, recovery affordances, visibility proof needs,
  and owner-surface metadata only. It must not template final Observation,
  Proposal, or Assist copy; the intervention and chatter layers keep the human
  voice live, evidence-shaped, and non-mechanical.
- Visible-intervention claims require `intervention-status`, transcript
  confirmation, or direct rendered fallback.
- Open-world Character pressure such as "stop templating voice" or "make the
  platform seamless" may rank voice or integration inspection affordances, but
  it must still stay silent when no hard law is violated and no immediate
  user-visible value is earned.
Last updated: 2026-04-18


Last updated (UTC): 2026-04-18

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
In v0.1.11 it also owns the visible intervention value engine: a
proposition-first deterministic selector that turns locally supported evidence
into the smallest high-value set of distinct visible Odylith blocks without
claiming ML calibration.

## Scope And Non-Goals
### Governance Intervention Engine owns
- The shared cross-host `ObservationEnvelope` intake contract.
- The shared `VisibleInterventionDecision` broker contract that chooses visible
  Markdown, hidden developer continuity, delivery channel, proof status,
  latency, and source fingerprints once for all host adapters.
- The proposition-level value engine contracts:
  `SignalEvidence`, `SignalProposition`, `InterventionValueFeatures`,
  `VisibleInterventionOption`, and `VisibleSignalSelectionDecision`.
- Hard gates for unsupported, stale, contradictory, generated-only,
  hidden-only, mixed non-current evidence, missing-evidence, weak-evidence,
  unknown visible labels or block kinds, label/block-kind mismatches,
  duplicate, and proposal-restatement propositions.
- Deterministic expected-value scoring, adaptive live budgets, and bounded
  subset selection for Risks, History, Insight, Observation, and Proposal.
- Proposition-first ambient stacking. Same-label blocks are allowed only when
  their duplicate keys and semantic signatures are distinct, evidence-qualified,
  and still inside the adaptive live budget.
- Semantic duplicate prevention is a hard selection constraint, not a renderer
  nicety. If two eligible options carry materially overlapping proposition
  signatures under different duplicate keys, or if sparse/incorrect producer
  metadata still carries the same normalized claim text, the selector must
  keep the stronger/actionable option and suppress the other before visible
  output.
- `Odylith Proposal` may bypass semantic-overlap suppression only when it has
  a concrete action and distinct proposition text. A proposal that repeats the
  exact Observation claim is still a duplicate, even when its payload contains
  an action.
- Adversarial selector diagnostics: selected/suppressed logs must expose
  hard-gate reasons, evidence-gate counts, pruned candidate counts, conflict
  graph size, enumerated subset count, selected utility, and latency.
- Hot-path ambient candidate generation must prefilter supported facts before
  voice rendering, cap rendered candidate payloads, and let the value engine
  decide final visibility from proposition identity rather than signal label.
- Ambient candidate rendering must avoid duplicate voice work: build the
  semantic body once, derive the ruled Markdown/plain labels deterministically,
  and spend voice-render cost only on candidates that survived support and
  strength prefilters.
- Ruled live-block canonicalization for Ambient/Observation/Proposal output;
  missing rulers are repaired, while `Odylith Assist` remains closeout-owned
  and outside the live ruled block.
- The live mid-turn conversation surface fast path used by Codex and Claude
  hooks, including teaser rendering, low-signal suppression, and host-parity
  shaping.
- Fact selection for `history`, `governance_truth`, `invariant`, `topology`,
  and `capture_opportunity` beats.
- Intervention thresholds for teaser, corroborated observation card, and
  proposal eligibility.
- The bootstrap intervention-value adjudication corpus and advisory selector
  report, including provenance and density gates that keep calibration loading
  disabled unless the artifact is explicitly publishable.
- Material Guidance Behavior contract evidence once it has already been
  compacted by the governance runtime. Passing guidance behavior stays quiet;
  failed, malformed, or unavailable guidance behavior can become one
  high-signal supported proposition through `alignment_evidence.py`.
- Compact Guidance Behavior platform-contract evidence. The intervention path
  consumes the same summary that proves benchmark/eval wiring, host mirrors,
  consumer bundle assets, and install guidance instead of deriving separate
  relevance or visibility policy locally.
- Material Agent Operating Character evidence from `alignment_evidence.py`.
  Passing Character checks stay quiet. Failed, malformed, or unavailable
  Character summaries can become one supported invariant with a concrete local
  recovery command, but they do not bypass the intervention value engine or
  render canned Character copy.
- Adaptive Character voice pressure is evidence for inspection, not permission
  to generate fixed posture language. If Character admits the move, the live
  intervention path remains silent unless the value engine independently earns
  a visible Observation or Proposal from current evidence.
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
  [Execution Engine](../execution-engine/CURRENT_SPEC.md).
- Human narration policy outside observation and proposal blocks; that belongs
  to [Odylith Chatter](../odylith-chatter/CURRENT_SPEC.md), which stays the
  closeout and broader narration layer.
- Stream audit storage or pending-proposal read models; that belongs to
  [Compass](../compass/CURRENT_SPEC.md).
- Unsafe auto-update flows where no safe CLI-backed helper exists yet.
- Public claims that the selector is ML-calibrated while the governed corpus is
  still in `quality_state=bootstrap`.

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
- Multiple ambient blocks may render in one chat when their propositions are
  distinct, supported, timely, and high value. The current budget is adaptive:
  base `1`, plus explicit diagnosis/planning, plus multiple high-materiality
  propositions, plus actionable proposal readiness, hard-capped at `4` live
  blocks and `3` ambient blocks.
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
- `src/odylith/runtime/intervention_engine/alignment_context.py`
  Hot-path alignment reader that feeds prompt, checkpoint, Stop, manual
  fallback, and status surfaces with the same compact Context Engine packet,
  Execution Engine snapshot summary, session-memory snapshot, delivery-ledger
  visibility state, and Tribunal summary. It reads only cached local runtime
  artifacts and precomputed delivery intelligence; it must not invoke provider
  calls, full context-store expansion, or repo-wide search while deciding
  chat visibility.
- `src/odylith/runtime/intervention_engine/alignment_evidence.py`
  Reusable hot-path evidence normalizer for the intervention engine. It merges
  legacy packet summaries with Context Engine packet summaries, folds compact
  session-memory evidence into stream-derived memory, gates empty runtime
  summaries out of evidence scoring, extracts material Execution Engine,
  Tribunal, guidance-behavior, and visibility-ledger facts, and returns one
  bounded target/ref model for signal scoring and repo-truth lookup.
- `src/odylith/runtime/intervention_engine/conversation_runtime.py`
  Shared ambient-signal selection, closeout Assist composition, and
  conversation-bundle assembly for subagent orchestration plus host-adoption
  summaries, including the bounded `affected_contracts` payload used by
  `Odylith Assist` to name touched or scoped governance contracts.
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
- `src/odylith/runtime/intervention_engine/delivery_ledger.py`
  Low-latency delivery read model that derives active chat-visible posture,
  recent Observation/Proposal/Ambient/Assist delivery, and pending proposal
  context from the Compass intervention stream without creating a second
  host-local truth store.
- `src/odylith/runtime/intervention_engine/visibility_contract.py`
  Shared delivery vocabulary and proof semantics for the intervention hot
  path. It owns host-family inference, visible-family classification,
  ledger-visible versus chat-confirmed detection, assistant-confirmation
  eligibility, and proof-status classification so status, broker, alignment,
  ledger, and ambient dedupe code cannot drift into separate interpretations
  of the same event.
- `src/odylith/runtime/intervention_engine/visibility_replay.py`
  Shared transcript-replay read model for branded blocks that have been
  generated, fallback-visible, or Stop-continuation-ready but have not yet
  been confirmed in the assistant transcript. It dedupes by display-aware
  confirmation key, repairs missing live rulers, keeps Assist outside live
  rulers, applies the live ambient/intervention budget, and feeds prompt,
  checkpoint, manual visible-intervention, status, and Stop surfaces.
- `src/odylith/runtime/intervention_engine/visibility_broker.py`
  Shared chat-visible decision broker consumed by Codex, Claude, manual
  fallback, Stop recovery, status probes, and tests. It is the only runtime
  surface allowed to decide whether an earned beat is visible, fallback-ready,
  assistant-render-required, or chat-confirmed.
- `src/odylith/runtime/intervention_engine/value_engine.py`
  Public facade for the proposition-first value engine. It re-exports the
  forward v0.1.11 runtime contract without preserving the removed block-first
  signal-ranker API.
- `src/odylith/runtime/intervention_engine/value_engine_types.py`
  Evidence/proposition/value contracts plus deterministic utility scoring.
  This owns `SignalEvidence`, `SignalProposition`,
  `InterventionValueFeatures`, `VisibleInterventionOption`,
  `VisibleSignalSelectionDecision`, evidence-confidence ceilings, and the
  `deterministic_utility_v1` posture.
- `src/odylith/runtime/intervention_engine/value_engine_selection.py`
  Hard suppression gates, duplicate collapse, proposal dependency checks,
  concrete proposal-action validation, adaptive live budgets, bounded subset
  enumeration, semantic-signature conflict edges, ambient-label crowding cost,
  and compact selected / suppressed decision logs. The selector caches labels,
  duplicate keys, normalized feature vectors, semantic tokens, and proposal
  action state before subset enumeration so latency is spent on subset value,
  not repeated string normalization.
- `src/odylith/runtime/intervention_engine/value_engine_corpus.py`
  Governed adjudication-corpus loading, provenance validation, density gates,
  advisory selector metrics, and the runtime rule that calibrated artifacts are
  not loadable until corpus quality is explicitly publishable.
- `src/odylith/runtime/intervention_engine/value_engine_event_metadata.py`
  Compact value-decision event metadata builder. It keeps selected/suppressed
  proposition proof logging out of the hot conversation renderer and stores
  only bounded evidence fingerprints and feature payloads in stream events.
- `src/odylith/runtime/evaluation/odylith_intervention_value_engine_benchmark.py`
  Advisory benchmark report for selector mechanism evidence. It reports
  precision, must-surface recall, duplicate visible rate, visibility-failure
  recall, no-output accuracy, p95 selector latency, corpus quality state, and
  calibration publishability without presenting those metrics as full
  `odylith_on` outcome proof.
- `src/odylith/install/value_engine_migration.py`
  v0.1.10 to v0.1.11 forward migration. It removes stale signal-ranker source
  artifacts, writes the new value-engine corpus when the bundled asset exists,
  and records the migration ledger under `.odylith/state/migrations/`.
- `src/odylith/runtime/intervention_engine/apply.py`
  CLI-first apply and decline handling for supported proposal bundles.
- `src/odylith/runtime/intervention_engine/cli.py`
  Thin `odylith governance intervention-preview` and
  `odylith governance capture-apply` entrypoints.
- `src/odylith/runtime/common/claude_cli_capabilities.py` and selected
  `src/odylith/runtime/surfaces/claude_host_*` /
  `src/odylith/runtime/surfaces/codex_host_*` hook adapters
  Host activation seams that must preserve the shared engine's visible
  Observation/Proposal contract while using each host's real transcript
  surface.

### Core public types
- `ObservationEnvelope`
  Fixed fields: `host_family`, `session_id`, `turn_phase`, `prompt_excerpt`,
  `assistant_summary`, `changed_paths`, `packet_summary`,
  `context_packet_summary`, `execution_engine_summary`, `memory_summary`,
  `tribunal_summary`, `visibility_summary`, `delivery_snapshot`, and
  `active_target_refs`.
- `VisibleInterventionDecision`
  Compact broker output carrying `visible_markdown`, `developer_context`,
  `delivery_channel`, `delivery_status`, `proof_required`,
  `no_output_reason`, `latency_ms`, source fingerprints, and the shared
  visibility summary reused by host payloads, status probes, and transcript
  tests.
- `SignalEvidence`
  Compact support row with source kind, source id/path, source fingerprint,
  freshness, confidence, excerpt, and evidence class.
- `SignalProposition`
  Stable proposition row with claim text, kind, support state, anchors,
  semantic signature, duplicate key, freshness state, evidence list, and
  source fingerprints.
- `InterventionValueFeatures`
  Deterministic value feature vector:
  correctness confidence, materiality, actionability, novelty, timing
  relevance, user need, visibility need, interruption cost, redundancy cost,
  uncertainty penalty, and brand risk.
- `VisibleInterventionOption`
  Candidate render option carrying one proposition, label, block kind, rendered
  Markdown/plain text, proof requirement, action payload, value features, and
  compact metadata.
- `VisibleSignalSelectionDecision`
  Selected and suppressed options, duplicate groups, no-output reason,
  selected block-set id, utility summary, proof posture, and decision-log
  payload.
- Host alignment context
  Compact, non-public payload consumed by host surfaces before the broker
  decides visibility. Required fields are `context_packet`,
  `execution_engine_summary`, `memory_summary`, `visibility_summary`,
  `delivery_snapshot`, and `tribunal_summary`. When an operator reports zero
  ambient highlights, zero signals, invisible Observations/Proposals, or a
  missing Assist, this context must infer the `B-096`/`CB-122` visibility
  recurrence, include the Governance Intervention Engine plus Context Engine,
  Execution Engine, memory backend, and Tribunal components, and force the
  Execution Engine next move into a recover lane until chat-visible proof is
  confirmed.
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
- In shipped prompt hooks, the visible user beat must use the host-visible
  channel or the assistant-render fallback, not merely any structured payload
  field. Codex carries the teaser through hook `systemMessage` plus
  `hookSpecificOutput.additionalContext` with fallback instructions. Claude
  splits prompt handling: `prompt-context` returns discreet JSON
  `hookSpecificOutput.additionalContext` with fallback instructions, while
  `prompt-teaser` prints the earned teaser as a best-effort stdout source when
  the host exposes it.
- Codex live-ready posture must not be inferred from `codex debug
  prompt-input` alone. That probe proves repo guidance reaches model context.
  The intervention engine requires `features.codex_hooks = true`,
  `.codex/hooks.json` wiring for prompt, Bash checkpoint, and stop hooks,
  direct `odylith codex ...` hook payload smoke, and assistant-render fallback
  proof before claiming the UX can be visible to the user. Current Codex
  `PostToolUse` schema exposes `Bash` only; native desktop write payloads
  remain parser-supported for tests and manual fallback but are not automatic
  hook coverage until the host exposes them.
- `stop_summary`
  May upgrade to a full `Odylith Observation` when corroboration exists, even
  when proposal readiness is still too low to surface `Odylith Proposal` yet.
  In shipped Codex and Claude host lanes, stop-summary is the fallback visible
  surface rather than the primary intervention moment. It should recover a
  missed late Observation and may pair that with a shared closeout Assist line
  when the closeout-side bundle is eligible.
- `post_edit_checkpoint` and `post_bash_checkpoint`
  are the primary visible intervention lanes. They may upgrade an earned
  observation into a proposal by attaching concrete changed-path evidence and
  governed targets, and should surface the earned Observation/Proposal beat
  visibly at the hook moment when the host supports it, or through the
  assistant-render fallback when the host keeps hook output hidden. On Codex,
  `post_bash_checkpoint` is the CLI name for the hookable Bash checkpoint
  surface; native desktop patch/exec payloads are manual/test fallback inputs,
  not automatic hook coverage. On Claude, direct edits and Bash writes are
  separate hook commands but must render the same shared intervention bundle
  shape.
- Codex `post_bash_checkpoint` grounding must use a repo-local latency cache
  before invoking `odylith start --repo-root .`. A cold or stale cache may run
  start once for the active session bucket; warm cache entries, including
  failed or launcher-unavailable attempts, must skip repeated start calls
  while still evaluating the command's changed paths, selective governance
  refresh, and visible intervention bundle on every hook.
- Claude `post_edit_checkpoint` and `post_bash_checkpoint` must stay
  synchronous. Async post-tool hooks can delay output to a later turn and
  suppress completion notices in normal Claude Code sessions, which breaks
  the live Observation/Proposal UX.
- Host payload builders intentionally carry two surfaces at once:
  - hidden developer context (`additionalContext` or
    `hookSpecificOutput.additionalContext`) with the full
    Observation/Proposal/Assist bundle for model continuity plus
    assistant-render fallback instructions for chat visibility
  - hook `systemMessage` with the earned Observation/Proposal beat and only
    failure-level governance status when that status materially changes the
    next move; this is useful host context but is not alone considered proof
    that the user saw the beat
- Host adapters must consume the shared `VisibleInterventionDecision` instead
  of deriving visibility policy locally. The same decision object feeds Codex
  prompt/post-bash/stop paths, Claude prompt/post-edit/post-bash/stop paths,
  manual `visible-intervention` fallback, and `intervention-status`.
- Host-composed conversation bundles must preserve the live-surface ambient
  payload separately from closeout ambient/supplemental signals. `Odylith
  Insight`, `Odylith History`, and `Odylith Risks` are live checkpoint beats;
  they must not disappear because the closeout bundle also has an
  `ambient_signals` object for Assist-side narration.
- Assistant-visible fallback context must not duplicate the exact same visible
  Markdown block into developer continuity. The fallback block carries the
  user-facing text once; developer continuity should retain only additional
  non-visible context such as Assist closeout state or anchor summaries. This
  keeps hidden hook paths useful without turning invisible intervention
  delivery into avoidable model-context token burn. The fallback instruction
  itself should stay compact; the signal, not framework prose, deserves the
  token budget.
- `odylith codex visible-intervention` and `odylith claude
  visible-intervention` render plain Markdown fallback output for the assistant
  to show directly when host hook display is unproven or hidden.
- `odylith codex intervention-status` and `odylith claude
  intervention-status` report static host readiness, a separate
  `chat_visible_proof` status for the active session, active UX lanes, recent
  ledger-visible delivery events, strict chat-confirmed event count, family
  visibility ratios for Teaser diagnostics, Ambient, Observation/Proposal,
  and Assist, pending proposal count, an exact assistant-visible replay block
  for unconfirmed branded events, and a fast smoke command.
  These commands are the cheap operator proof before claiming a session has
  live Observation/Proposal/Ambient/Assist delivery; `Activation: ready` alone
  is static wiring, not session-visible proof.
- `assistant_fallback_ready`, `assistant_render_required`, and structured
  `systemMessage` generation are hidden-ready or assistant-required states,
  not session-visible proof. The delivery ledger may retain those events for
  Stop replay and continuity, but they stay pending until a visible delivery
  path or strict transcript confirmation exists.
- `manual_visible`, `best_effort_visible`, and `stop_continuation_ready` are
  ledger-visible fallback states. They prove Odylith produced assistant-facing
  visible Markdown through a fallback path, but they do not prove the host chat
  transcript contains that Markdown. Status surfaces must report these as
  `ledger_visible_unconfirmed` or `ledger_visible_with_pending_confirmation`
  until exact assistant transcript confirmation promotes the event.
- `assistant_chat_confirmed` is recorded only when a status probe or Stop path
  sees the exact Odylith Markdown from a prior non-visible or fallback-visible
  beat in the latest assistant message. A generated hook payload,
  `systemMessage`, or `additionalContext` field must never promote itself to
  chat-visible proof.
- Delivery snapshots must infer host family from legacy `render_surface`
  values such as `codex_visible_intervention` or
  `claude_visible_intervention` when older events lack an explicit
  `host_family`, so status does not undercount visible fallback rows during
  v0.1.10 to v0.1.11 migration.
- Stop-summary hooks may block once with a continuation reason when a real
  Observation or `Odylith Assist:` closeout was generated but is not already
  visible in the last assistant message. The `stop_hook_active` guard prevents
  loops.
- Stop-summary is also the hard visibility fallback for earlier live beats.
  If a prompt/checkpoint generated an Ambient Highlight, `Odylith Observation`,
  or `Odylith Proposal` through a host path that may have stayed hidden, Stop
  may replay the bounded set of distinct unconfirmed live beats before the
  Assist line and send the combined text through the same one-shot continuation
  mechanism. Manual-visible, best-effort, and Stop-continuation rows remain
  replayable until exact transcript confirmation proves the assistant message
  actually carried the Markdown.
- Stop-summary Assist may use concrete validation/pass signals from the
  assistant summary when changed paths are unavailable. This recovery path is
  proof-only: it may say the proof stayed tight, but it must not claim
  artifact updates without changed-path or governed-target evidence.
- Stop-summary Assist may also recover from explicit user feedback about
  missing Odylith visibility, ambient highlights, Observations, Proposals,
  Assist, hooks, or chat surfacing. This lane is intentionally narrow: it may
  say the UX signal stayed alive, but it must stay silent for ordinary
  low-signal short turns.
- Stop-summary visibility dedupe must compare the labels in the generated
  visible text, not merely the existence of any prior Odylith label. A prior
  Observation is not proof that the current Assist closeout was already shown.
- Ambient Highlight duplicate suppression must make the same distinction.
  A prior teaser, card, or proposal that only reached `assistant_fallback_ready`
  or another hidden-ready hook surface is not proof that the human saw the
  beat. Ambient recovery may reuse that moment until a proven visible channel
  such as `manual_visible_command`, `stdout_teaser`, or
  `stop_one_shot_guard` has carried it.
- Ambient Highlight eligibility shares the post-tool teaser floor: once a
  post-edit or post-bash moment has a real governed fact and is teaser-worthy,
  it should render as a concrete `Odylith Insight`, `Odylith History`, or
  `Odylith Risks` line instead of disappearing behind a stricter ambient-only
  score threshold.
- When Ambient Highlight wins the visible live slot, it is the recorded live
  beat for that moment. The runtime should not also append a generic teaser
  event for the same candidate, and the ambient event must carry the same
  intervention key and semantic signature so continuity and dedupe follow the
  human-facing signal instead of a hidden precursor.
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
- Closeout recovery may name affected workstream, component, diagram, or bug
  IDs from bounded request, packet, changed-path, or target-ref truth. It must
  distinguish updated governed records from contracts merely kept in scope.
- Apply and decline are part of the same continuity chain. Terminal proposal
  events must preserve `moment_kind` and semantic signature so later runtime
  consumers can still understand which governed moment was applied, declined,
  or rendered stale.
- Delivery metadata is part of the same event stream. Teaser, ambient,
  Observation, Proposal, and Assist events may carry `delivery_channel`,
  `delivery_status`, and `render_surface` so `intervention-status` can answer
  whether a specific Codex or Claude session is actually visible-ready without
  doing fresh repo search or relying on host payload faith.
- Value-decision metadata is part of the live event stream for selected
  Teaser/Ambient/Observation/Proposal events. Events must carry compact
  selected and suppressed proposition ids, duplicate groups, semantic
  signatures, feature vectors, evidence fingerprints, net utility, and proof
  posture. Assistant chat confirmation must preserve that metadata while
  moving delivery state to `assistant_chat_confirmed`.
- Distinct ambient propositions must keep distinct event identity even when
  they share the same visible label. Same-label `Odylith Risks`, `Odylith
  History`, or `Odylith Insight` blocks use selected candidate ids as
  `intervention_key` values; transcript confirmation must be able to confirm
  each rendered block independently from one assistant message.
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
- All live Odylith teaser, ambient, Observation, and Proposal output must be
  visibly bounded by Markdown horizontal rules (`---`) before and after the
  Odylith-owned text so operators can distinguish Odylith intervention copy
  from host-agent narration. `Odylith Assist` is exempt because it remains the
  final blended closeout paragraph.
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
- The default voice renderer must keep the structural frame deterministic while
  deriving the body from supported proposition content: fact headline, fact
  detail, supporting evidence, and proposal action rationale. Moment kind may
  still steer eligibility and label choice, but it must not be the primary
  sentence-template selector.
- Voice variation must stay deterministic across Codex, Claude, and all lanes
  for the same observation envelope. The product should feel evidence-native,
  not random, and never like a phrase bank with rotating stock stems.
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
- `odylith codex intervention-status`
  Report Codex static hook readiness, session `chat_visible_proof`, and the
  Compass-derived visible-delivery ledger for the active session.
- `odylith claude intervention-status`
  Report Claude project-hook readiness, session `chat_visible_proof`, and the
  Compass-derived visible-delivery ledger for the active session.

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
- The visibility ledger also derives from Compass stream kinds
  `intervention_teaser`, `ambient_signal`, `intervention_card`,
  `capture_proposed`, and `assist_closeout`, using delivery metadata rather
  than a second mutable status file.
- Apply must refresh only the touched governed surfaces. It must not widen into
  a full-repo sync just to close one proposal.
- Apply must reject stale terminal bundles and preview-only bundles before any
  governed write begins.

## Composition
- [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md) supplies
  bounded packet and anchor truth.
- [Delivery Intelligence](../delivery-intelligence/CURRENT_SPEC.md) supplies
  posture and lane context through `delivery_snapshot`.
- [Execution Engine](../execution-engine/CURRENT_SPEC.md) supplies
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
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_delivery_status.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine_apply.py tests/unit/runtime/test_intervention_engine_performance.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_conversation_surface.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_intervention_host_surface_runtime.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_claude_host_prompt_context.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py tests/unit/runtime/test_claude_host_post_bash_checkpoint.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_claude_host_stop_summary.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-04-16 · Implementation:** Hardened intervention chat-visible delivery with a shared broker, assistant-render-required proof states, transcript confirmation, D-038 proposal visibility gating, and focused runtime/browser validation.
  - Scope: B-096
  - Evidence: src/odylith/runtime/intervention_engine/visibility_broker.py, tests/integration/runtime/test_intervention_visibility_browser.py +1 more
- **2026-04-15 · Implementation:** Completed intervention chat-visibility hardening: Codex and Claude now report assistant-visible readiness, visible-intervention renders Observation/Proposal/Assist Markdown, Stop Assist recovers from validation proof without claiming artifacts, and CB-121 plus B-096 governance records were updated.
  - Scope: B-096
  - Evidence: odylith/casebook/bugs/2026-04-16-intervention-hook-payloads-can-be-generated-but-never-reach-chat-visible-ux.md, src/odylith/runtime/intervention_engine/host_surface_runtime.py +1 more
- **2026-04-15 · Implementation:** Fixed intervention chat visibility contract: assistant-render fallback, visible-intervention CLI, Codex Bash-only hook truth, Stop one-shot Assist recovery, and CB-121 casebook capture.
  - Scope: B-096
  - Evidence: odylith/casebook/bugs/2026-04-16-intervention-hook-payloads-can-be-generated-but-never-reach-chat-visible-ux.md, src/odylith/runtime/intervention_engine/host_surface_runtime.py +1 more
<!-- registry-requirements:end -->

## Feature History
- 2026-04-14: Promoted Governance Intervention Engine into a first-class Registry component so Codex and Claude can share one portable conversation observation and governed proposal runtime instead of host-local intervention heuristics. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Shipped the fixed user-facing labels `Odylith Observation` and `Odylith Proposal`, the single-confirmation proposal apply contract, the future-ready voice-pack seam, and Atlas diagram `D-038` to keep runtime, governance, and maintainer guidance aligned. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Hardened the product contract so rich markdown survives the full host and Compass path, duplicate suppression keys stay causal rather than overly coarse, proposal apply is all-or-nothing for CLI-safe bundles, and warm-cache latency stays covered by focused regression tests. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Extended intervention lifecycle events to carry prompt memory and rich pending-proposal display payloads so later hooks keep reasoning from the human conversation and Compass can expose delightful proposal previews without rebuilding them downstream. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Split rich reasoning signature from stable continuity identity, added a cross-phase continuity runtime, and allowed first-time Proposal upgrades to surface without re-announcing a duplicate Observation. This made teaser, Observation, and Proposal feel like one evolving thought instead of three disconnected hook artifacts. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-16: Added a delivery ledger and host `intervention-status` commands so Codex and Claude can prove static readiness, active UX lanes, recent proven-visible delivery, pending proposal state, and manual fallback smoke without treating hook payload generation as chat visibility. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-16: Extended closeout Assist bundles with bounded affected-contract IDs so Codex and Claude can show the governed workstream, component, diagram, or bug contract involved even when the final visible beat is validation-only. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-16: Hardened live UX surfacing so Ambient Highlight is a distinct checkpoint/stop lane, ambient beats no longer lose to stale teasers after evidence matures, Stop can recover meaningful Assist from explicit visibility-feedback turns even when the final answer is short, and visible-delivery dedupe only suppresses exact generated labels. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
- 2026-04-16: Routed unseen Ambient Highlight, Observation, and Proposal beats through the same Stop one-shot continuation path as Assist, so host-hidden checkpoint output no longer leaves the user seeing only `Odylith Assist`. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
- 2026-04-16: Added explicit Markdown horizontal-rule boundaries around live teaser, ambient, Observation, and Proposal output so Odylith-owned intervention copy is visibly separated from host-agent narration, while `Odylith Assist` remains blended as the final closeout line. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
- 2026-04-17: Replaced moment-kind phrase-bank intervention copy with proposition-native voice composition: live text keeps fixed labels/rulers/confirmation structure while deriving the claim, consequence, and proposal bullets from supported facts and action rationales. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-16: Repaired Ambient Highlight reachability by lowering the live ambient floor to the post-tool teaser floor and by allowing hidden-ready duplicate teaser/card moments to recover as ambient lines until a proven visible channel has carried the beat. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
- 2026-04-16: Tightened delivery-ledger proof so `assistant_fallback_ready` and structured hook context no longer count as chat-visible delivery; they stay available for Stop replay without letting status or duplicate suppression pretend the user already saw the beat. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
- 2026-04-16: Fixed the host-composed live ambient path so checkpoint bundles preserve `live_ambient_signals` and emit concrete Ambient Highlight events instead of falling back to generic teasers. The same change removed duplicate visible Markdown and shortened fallback instruction prose to lower hidden-context token overhead. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
- 2026-04-16: Made Ambient Highlight the single recorded live beat when it wins the slot, carrying the candidate intervention key and semantic signature so continuity dedupes the visible ambient signal instead of logging a generic teaser plus ambient duplicate. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
- 2026-04-16: Added cached Codex post-bash grounding so repeated edit-like hooks no longer rerun slow or failing `odylith start` probes on every command, while each hook still evaluates selective sync and live intervention output. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
- 2026-04-17: Hardened the v0.1.11 Visible Intervention Value Engine against adversarial selector inputs: fabricated high scores now need evidence, weak evidence cannot masquerade as high correctness, same-label ambient blocks can stack only when propositions are distinct, concrete proposal actions are required, and candidate floods are pruned before bounded subset enumeration. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-123`)
- 2026-04-17: Expanded v0.1.11 QA with counterfactual tests for hidden-confidence inflation, missing confidence defaults, anchor-only governed support, deterministic input order, strict corpus provenance, ambient fact-flood prefiltering, same-label ambient event logging, and D-038 browser contract drift. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-123`)
- 2026-04-17: Fixed same-label ambient proof identity so two distinct high-value blocks in one assistant message write separate candidate keys and transcript confirmation proves both instead of collapsing them into one visible event. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bugs: `CB-122`, `CB-123`)
- 2026-04-17: Split fallback-visible delivery from strict assistant transcript proof in `intervention-status`: manual/best-effort/Stop continuation rows now report as ledger-visible but unconfirmed, status renders family visibility ratios for Teaser diagnostics, Ambient, Observation/Proposal, and Assist, exact assistant messages can promote fallback-visible events once, and legacy visible rows infer host family from `render_surface` during v0.1.11 migration. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bugs: `CB-122`, `CB-123`)
- 2026-04-17: Centralized intervention visibility semantics in `visibility_contract.py` so delivery ledger, visibility broker, status, alignment context, and ambient dedupe share one definition of host inference, visible family, ledger-visible, chat-confirmed, pending confirmation, and proof-status states. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bugs: `CB-122`, `CB-123`)
- 2026-04-17: Added shared transcript replay for true chat visibility: pending hidden, manual-visible, best-effort, and Stop-continuation blocks now replay as exact ruled Markdown through prompt/checkpoint fallback, `visible-intervention`, `intervention-status`, and Stop until `assistant_chat_confirmed` proves the assistant transcript contains the block. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bugs: `CB-122`, `CB-123`)
- 2026-04-17: Added `alignment_evidence.py` so Context Engine packets, Execution Engine recovery constraints, compact session memory, Tribunal scope/case signals, and delivery-ledger proof feed one bounded intervention evidence model. Empty runtime summaries no longer inflate weak prompts, while material alignment facts can shape the same value-engine decision without repo-wide search or context-store expansion. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bugs: `CB-122`, `CB-123`)
- 2026-04-17: Integrated Guidance Behavior summaries into the intervention evidence cone: passing summaries remain non-chatty, failed/malformed/unavailable guidance behavior becomes one supported `guidance_behavior_contract` fact, and the same value-engine path consumes it without provider calls, repo-wide scans, or context-store expansion. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-123`)
- 2026-04-17: Added the Guidance Behavior platform end-to-end contract to the compact evidence cone so benchmark/eval wiring, Codex and Claude host mirrors, consumer bundle assets, and install guidance empower the same intervention decision without hot-path validation or provider calls. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-123`)
- 2026-04-17: Extended the Guidance Behavior platform contract with live/source-bundle byte-parity checks so intervention evidence, host guidance, benchmark corpora, and governed program/spec truth cannot silently diverge between source-local, dogfood, and consumer lanes. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-123`)
- 2026-04-18: Wired Adaptive Agent Operating Character into the alignment evidence cone as local evidence, not scripted voice: passing checks remain silent, contract failures become a single high-signal invariant with recovery affordance, and the live intervention value engine still owns whether and how anything is shown. (Plan: [B-110](odylith/radar/radar.html?view=plan&workstream=B-110))
- 2026-04-18: Tightened Character/Intervention boundary QA so proof-gathering commands such as `intervention-status` and `visible-intervention` stay silent admissible local actions, while actual visible-UX claims still require ledger proof, transcript confirmation, or rendered fallback evidence. (Plan: [B-110](odylith/radar/radar.html?view=plan&workstream=B-110))
