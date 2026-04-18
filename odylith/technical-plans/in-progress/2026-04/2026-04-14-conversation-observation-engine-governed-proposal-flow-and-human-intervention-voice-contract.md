Status: In progress

Created: 2026-04-14

Updated: 2026-04-17

Backlog: B-096

Goal: Ship a first-class conversation observation engine under
`src/odylith/runtime/intervention_engine/` that observes live Codex and Claude
session evidence, turns corroborated governance truth into humane in-flow
`**Odylith Observation**` beats, upgrades explicit governed write suggestions
into single-confirmation `Odylith Proposal` bundles, and keeps the whole
experience governed across runtime, Registry, Atlas, Radar, Casebook, Compass,
and maintainer guidance. The UX and voice are part of the product contract in
this slice, not polish: interventions must feel friendly, delightful, soulful,
insightful, simple, clear, accurate, precise, and above all else human, while
staying timely, judicious, non-repetitive, and never mechanical.

v0.1.11 now hardens this slice around the Visible Intervention Value Engine:
Odylith surfaces propositions, not block labels. The runtime decides from a
supported proposition ledger, deterministic expected value, hard visibility
proof, duplicate collapse, and a small constrained subset optimizer. This is
not shipped as ML calibration; it is `deterministic_utility_v1` with governed
adjudication hooks and bootstrap-quality reporting until real transcript
density earns anything stronger.

Assumptions:
- V1 is one shared cross-host core. Codex and Claude adapters may differ only
  in hook payload collection and host-output envelopes, not in intervention
  reasoning or proposal assembly.
- The user-facing labels are fixed in this release:
  `**Odylith Observation**` for the corroborated markdown block and
  `Odylith Proposal` for the governed write bundle.
- Proposal confirmation phrase is fixed for this release:
  `apply this proposal`.
- The rendered confirmation cue must stay visually quiet, for example:
  `To apply, say "apply this proposal".`
- Future release work may add voice packs or operator-selectable voice modes,
  but this release ships one default Odylith brand voice only.
- Intervention reasoning must stay on the hot-path evidence cone: prompt
  excerpts, assistant summary, changed paths, active packet refs, delivery
  snapshot, local governance indices, and existing Compass/runtime state.
- The live mid-turn surface should stay intervention-engine-owned. Chatter
  remains the broader narration and final Assist layer instead of becoming the
  hot path for prompt, stop, post-edit, or post-bash intervention rendering.
- Live Odylith ambient blocks may stack when they are distinct, supported, and
  high value. The first v0.1.11 live budget is adaptive: up to `3` ambient
  blocks plus at most one Observation and one Proposal, hard-capped at `4`
  live blocks; `Odylith Assist` is excluded and remains closeout-owned.
- The runtime posture for v0.1.11 is `deterministic_utility_v1`. Calibration
  artifacts may exist only as offline advisory material and cannot be loaded
  by runtime unless corpus quality gates mark them `publishable=true`.
- The v0.1.10 signal-ranker direction is cut hard. v0.1.11 ships migration
  logic that removes stale signal-ranker source artifacts and writes the new
  value-engine corpus/ledger instead of keeping a compatibility shim.
- Safe apply in V1 is CLI-first and limited to surfaces where Odylith already
  has deterministic create helpers. Preview may cover richer update or reopen
  paths before apply supports them.
- The advanced fast-path algorithm is two-stage: first a cheap semantic
  prefilter decides whether this turn has governed signal at all; only then
  may repo-truth lookup, dedupe, and proposal assembly run.
- Guidance Behavior Enhancements are part of the v0.1.11 evidence cone, not a
  side validator. Relevant packets carry a compact guidance-behavior summary,
  Execution Engine snapshots reuse its validator command, Memory Contracts
  preserve the compact summary, intervention evidence treats material failures
  as one high-signal contract fact, and the Tribunal-ready signal remains
  precomputed.
- Guidance Behavior is also a shipped guidance-surface contract. The
  deterministic validator must prove that Codex guidance, Claude guidance,
  installed command/skill shims, product guidance, and consumer/dogfood/
  source-local lane instructions all point to the same CLI-first proof path.
- The validator now includes
  `odylith_guidance_behavior_platform_end_to_end.v1`: benchmark/eval wiring,
  host skill and command mirrors, bundled consumer assets, and install guidance
  are checked as one platform contract instead of separate green islands.
  Live `odylith/` guidance/spec/corpus truth and shipped source-bundle mirrors
  must also be byte-identical, so consumer, dogfood, and source-local lanes do
  not drift after a maintainer-only edit.
- Rich reasoning signature and stable continuity identity are separate on
  purpose. The engine may reason from more evidence as a moment matures, but
  teaser, Observation, and Proposal should still feel like one evolving
  session-local thought instead of three different hook artifacts.

Constraints:
- The observation/proposal experience is a make-or-break brand contract. Do
  not ship a renderer that reads like a rigid template engine, boilerplate
  alert box, or mechanical governance bot.
- Observations must lead with the non-obvious fact that changes the next move,
  not a bland recap of session state.
- Early low-signal moments stay lightweight and suppress repeated beats for the
  same causal point instead of spamming branded blocks.
- At most one full `Odylith Observation` card may appear per turn, no
  duplicate full cards may recur for the same causal point in the active
  session, and no governed write may happen before explicit confirmation.
- Duplicate semantic propositions are a hard gate across Risks, History,
  Insight, Observation, and Proposal. Proposal may coexist only when it adds a
  concrete next step beyond the Observation, not when it restates it.
- Caller-provided scores are never enough by themselves. A visible proposition
  must carry local grounding evidence, non-stale evidence freshness, and enough
  evidence confidence for the declared correctness to be plausible.
- Ambient dedupe is proposition-first, not label-first. Two `Odylith Risks`
  blocks may render in one turn only when they carry distinct high-value
  propositions, while exact or semantic duplicates collapse before rendering.
- Candidate floods are bounded before optimization: the selector prunes to the
  top evidence-qualified candidates, enumerates only a small independent-set
  space, and logs pruned/eligible counts so latency regressions are visible.
- Guidance-behavior validation must stay off the live hot path. Prompt,
  packet, memory, intervention, and status lanes may read only the compact
  summary, fingerprints, case ids, failed check ids, and validator command; the
  full validator runs as explicit proof, not as inline signal selection.
- Missing live rulers are repaired into canonical ruled Markdown; they are not
  a reason to drop a good supported signal. Assist is never wrapped in the
  live ruled block.
- The same change must update the runtime implementation, tests, governed
  specs, workstream/plan truth, Atlas topology, and maintainer-side guidance so
  the UX contract cannot quietly drift between code and docs.
- Governed writes must remain CLI-first where a first-class Odylith command
  exists. Do not hand-author governed source truth that an existing command
  already owns.

Reversibility: The engine is modular and reversible. If the shared core proves
too aggressive or the voice contract needs a rapid rollback, the new runtime
package, host hook wiring, CLI wrappers, and governed component records can be
removed or softened without undoing unrelated Codex, Claude, Compass, or
execution-governance behavior. Focused unit coverage should keep that rollback
legible.

Boundary Conditions:
- Scope includes the new intervention-engine package, shared contracts, CLI
  wrappers, event-stream state, host-hook integration, Chatter bundle
  integration, Compass pending-proposal derivation, safe proposal apply for
  supported create paths, governed record updates, and explicit UX/voice
  guidance updates.
- Scope excludes user-selectable voice packs, per-surface approval flows,
  wide fresh repo search just to make interventions sound smarter, and unsafe
  update automation where no CLI-backed helper exists yet.

Related Bugs:
- [CB-122](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-17-intervention-hooks-report-ready-while-chat-sees-zero-visible-odylith-beats.md)
- [CB-123](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-17-bootstrap-signal-corpus-can-be-mistaken-for-calibrated-ml-quality.md)

## v0.1.11 Execution-Wave Program
- Umbrella: `B-096`.
- Release target: `release-0-1-11`.
- Program source:
  [B-096.execution-waves.v1.json](/Users/freedom/code/odylith/odylith/radar/source/programs/B-096.execution-waves.v1.json)
- Waves:
  `B-105` governance binding,
  `B-106` proposition value engine,
  `B-107` host visibility and ruler canonicalization,
  `B-108` adjudication corpus and advisory benchmark,
  `B-109` release proof.

## Learnings
- [ ] Odylith interventions are only compelling if the markdown block changes
      the user's next move quickly. If the copy sounds like static compliance
      prose, the brand loses even when the facts are correct.
- [ ] The strongest intervention beat is often a topology, invariant, or prior
      governance memory connection that the user did not explicitly ask for but
      immediately benefits from seeing.
- [ ] Proposal UX must feel like one coherent governed action bundle, not four
      unrelated surface chores masquerading as automation.
- [ ] The markdown formatting itself is product behavior. If Observation or
      Proposal blocks lose their spacing, heading order, or scanability in the
      host or Compass path, the brand contract has already regressed.
- [ ] Voice is part of the runtime contract. If Chatter, host hooks, Compass,
      Registry specs, and maintainer guidance disagree about tone, the product
      will drift back toward mechanical narration.
- [ ] Future voice-pack support needs an explicit seam in the contract now so
      this release does not hardwire incidental phrasing deep into host
      adapters.
- [ ] Preview-only proposal bundles must stay all-or-nothing. Partial apply of
      just the currently supported surfaces would make the confirmation model
      lie.
- [ ] Session memory must preserve the user's prompt through teaser, observation,
      proposal, apply, and decline events. Later hooks should never reason from
      Odylith's own pending/applied summaries when prompt truth is available.
- [ ] Cross-lane guidance is part of the shipped product contract here. Root
      AGENTS, install-managed consumer guidance, product guidance, and
      maintainer benchmark/demo guidance all need the same Observation/Proposal
      labels, prompt-rooted contract, and anti-mechanical voice rules.
- [ ] Missing launcher-backed anchor resolution is not permission to silence a
      real prompt-submit teaser. The anchor summary may degrade; the earned
      intervention beat should survive.
- [ ] Prompt-submit teaser surfacing must stay user-visible and discreet at
      once, but the implementation must obey the real host contract. Claude
      Code needs split prompt hooks: one JSON context hook for discreet anchor
      continuity and one plain-stdout teaser hook for transcript visibility.
      Codex uses structured `systemMessage`.
- [ ] Claude Code async hooks are the wrong lane for the primary live
      Observation/Proposal UX. Async is fine for background diagnostics, but
      post-edit intervention output must be synchronous if users are meant to
      see it at the moment it matters.
- [ ] Bare changed paths with no governed fact should stay silent. Near-zero
      latency matters, but fast low-signal filler is still product debt.
- [ ] If the same moment earns a teaser first, then an Observation, then a
      Proposal, the user should feel one evolving intervention arc rather than
      three disconnected branded announcements.
- [ ] Codex desktop edits are not always Bash. Native `apply_patch` and
      command-style exec payloads must trigger the same visible checkpoint lane
      as Bash, or the engine can be technically active while the user sees no
      mid-turn Observation/Proposal after real Codex edits.
- [ ] Chat visibility needs its own delivery ledger. Green hook payload tests
      prove computation, not lived UX; operators need a cheap host/session
      status surface that says which lanes are armed, what was recently
      visible-ready, and how to force the fallback Markdown now.
- [ ] Seed cases are not ML. A bootstrap corpus is valuable regression
      coverage, but public-quality precision/recall or calibrated-threshold
      claims require dense, real, non-synthetic transcript adjudication.
- [ ] The unit of selection is the proposition. Labels such as Risks, History,
      Insight, Observation, and Proposal are render outputs after value,
      support, duplicate, visibility, and proposal-dependency checks.
- [ ] More than one ambient block can be useful when the propositions are
      genuinely distinct and high value; the cap should be adaptive and
      noise-aware, not effectively hard-coded to one.
- [ ] Structural templating is necessary for labels, rulers, proof, and
      confirmation, but the intervention body must be proposition-native. Fact
      headlines/details and action rationales should drive claim,
      consequence, and next-step copy; moment kind should not choose a canned
      sentence family.
- [ ] Guidance behavior only becomes product behavior when the same compact
      summary and explicit validator travel through Context Engine, Execution
      Engine, Memory Contracts, Governance Intervention Engine,
      Tribunal-ready evidence, benchmark reports, host contracts, installed
      skills, and consumer-lane guidance.

## Must-Ship
- [x] Add `src/odylith/runtime/intervention_engine/` as a first-class shared
      runtime package with contracts for `ObservationEnvelope`,
      `GovernanceFact`, `InterventionCandidate`, `CaptureAction`,
      `CaptureBundle`, and `InterventionBundle`.
- [x] Add thin CLI wrappers for
      `odylith governance intervention-preview` and
      `odylith governance capture-apply`.
- [x] Consolidate conversation-signaling bundle composition under
      `src/odylith/runtime/intervention_engine/conversation_runtime.py` so the
      structured `intervention_bundle` and closeout/ambient bundles share one
      owning package instead of split orchestration-era homes.
- [x] Wire prompt-submit, stop-summary, and post-edit/post-bash host surfaces
      so teaser, observation, and proposal phases use the same shared engine
      across Codex and Claude.
- [x] Keep the live mid-turn path intervention-engine-owned and lightweight,
      with Chatter narrowed back to narration policy and final Assist closeout.
- [x] Derive pending proposal state from Compass intervention/proposal events
      and expose that derived state in the Compass runtime snapshot instead of
      creating a second source of truth.
- [x] Enforce the product UX contract in code and governed records:
      `Odylith Observation`, `Odylith Proposal`, one-card-per-turn,
      confirmation-first writes, low-signal suppression, and human non-templated
      voice.
- [x] Support safe CLI-backed apply for deterministic create flows across
      Radar, Registry, Atlas, and Casebook where the helper already exists or
      can be safely added in this slice; preview-only update/reopen paths stay
      clearly marked.
- [x] Add focused tests for observation/proposal assembly, host integration,
      Compass pending state, and safe apply behavior.
- [x] Register the new Registry component
      `governance-intervention-engine` and update the `odylith-chatter`,
      `compass`, and `execution-governance` component specs.
- [x] Add or update the bound Atlas topology record for conversation
      observation to governed proposal flow.
- [x] Update maintainer-side and host-side guidance so the intervention UX and
      voice remain explicit maintainer policy, not tribal knowledge.

## Should-Ship
- [x] Keep the shared engine deterministic and cheap enough that prompt hooks
      can preview observation value without turning every turn into a heavy
      reasoning pass.
- [x] Move from first-match fact narration to staged moment selection so the
      engine chooses one dominant governed beat using urgency, novelty,
      continuity, and proposal-readiness instead of flattening the first fact
      into templated copy.
- [x] Add a cheap semantic signal kernel plus cached session-memory snapshot
      so the hot path can reason over continuity and escalation without paying
      full repo-truth or full stream-read cost on every turn.
- [x] Add stable cross-phase moment identity and continuity lookup so prompt,
      stop, and edit/bash hooks evolve the same intervention moment instead of
      churning keys whenever new evidence appears.
- [x] Make continuity prefer exact stable moment key over signature fallback so
      two distinct moments with similar language do not bleed into one another.
- [x] Cache derived stream summaries for session memory, pending proposals, and
      moment continuity so the hot path avoids reparsing or re-walking the
      same event tail on every live hook.
- [x] Preserve a clear contract seam for future voice-pack selection without
      exposing that unfinished customization surface in this release.
- [x] Emit Compass stream events for teaser, observation, proposal, apply, and
      decline so later runtime surfaces can reason about proposal lifecycle.
- [x] Add low-latency `odylith codex intervention-status` and
      `odylith claude intervention-status` surfaces that report static host
      readiness, active UX lanes, delivery-ledger evidence, pending proposals,
      and a smoke command without slow host probes.
- [x] Extend intervention stream events with delivery metadata for
      Teaser/Ambient, Observation, Proposal, and Assist so visibility status is
      derived from Compass rather than a second mutable status file.
- [x] Replace the partial block-first signal-ranker direction with a
      proposition-first value-engine package:
      [value_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/value_engine.py),
      [value_engine_types.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/value_engine_types.py),
      [value_engine_selection.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/value_engine_selection.py), and
      [value_engine_corpus.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/value_engine_corpus.py).
- [x] Add governed value-engine contracts for `SignalEvidence`,
      `SignalProposition`, `InterventionValueFeatures`,
      `VisibleInterventionOption`, and `VisibleSignalSelectionDecision`.
- [x] Add deterministic utility scoring, hard gates, conflict/duplicate
      collapse, proposal dependency checks, adaptive live budget, and bounded
      subset enumeration.
- [x] Add governed bootstrap corpus source:
      [intervention-value-adjudication-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/intervention-value-adjudication-corpus.v1.json).
- [x] Add advisory benchmark/report code that separates deterministic runtime
      quality from full `odylith_on` outcome proof and keeps calibration
      publishability false while density gates fail.
- [x] Add v0.1.10 to v0.1.11 migration logic that removes stale signal-ranker
      artifacts, writes the value-engine corpus where applicable, and records
      `.odylith/state/migrations/v0.1.11-visible-intervention-value-engine.v1.json`.
- [x] Add adversarial/counterfactual hardening so fabricated high-score
      candidates without evidence, weak evidence masked as high correctness,
      same-label ambient collisions, non-concrete proposals, and candidate
      floods are all tested and logged without provider calls.
- [x] Run a hard QA pass that adds regression tests for hidden-confidence
      inflation, missing confidence defaults, governed anchor-only support,
      same-label duplicate collapse, deterministic input-order handling,
      strict corpus provenance, ambient fact-flood prefiltering, same-label
      event logging, and D-038 browser-surface contract drift.
- [x] Harden the end-to-end value/proof layer so semantic duplicates collapse
      even when duplicate keys differ, actionable Proposal blocks can still
      coexist with their Observation when they add concrete work, intervention
      events carry compact selected/suppressed value-decision metadata, and
      assistant chat confirmation preserves that proof metadata.
- [x] Add aggressive visibility-proof regression coverage for multiple
      same-label ambient blocks in one assistant message: distinct candidate
      ids must write distinct event keys, transcript confirmation must confirm
      both blocks independently, and hidden fallback-ready output must never
      collapse separate supported propositions into one proven-visible event.
- [x] Cut hot-path drag without lowering signal quality: cache selector labels,
      duplicate groups, normalized feature vectors, semantic tokens, and
      proposal-action state before subset enumeration; derive ambient Markdown
      from one voice-rendered body instead of rendering plain and Markdown
      separately; move value-decision event metadata into a small focused
      module so `conversation_surface.py` stays below the 1200 LOC hard line.
- [x] Tighten adversarial selector edges: fail closed on unknown live labels
      and block kinds, keep `Odylith Assist` out of the live value path,
      suppress mixed non-current evidence even when anchor refs are present,
      and collapse duplicate propositions from normalized claim text when
      duplicate keys or semantic signatures are missing or misleading.
- [x] Tighten label/kind and proposal-restatement safety: ambient labels must
      remain ambient, Observation/Proposal labels must use their matching live
      block kind, and a concrete Proposal still suppresses as duplicate when
      it repeats the exact Observation proposition instead of adding distinct
      next-step content.
- [x] Replace moment-kind phrase-bank voice rendering with proposition-native
      composition. Teaser, Ambient, Observation, and Proposal keep deterministic
      labels/rulers/confirmation structure, but their body text now comes from
      supported fact claim/detail content and proposal action rationales.
- [x] Split fallback-visible delivery accounting from strict assistant transcript
      proof. `intervention-status` now reports manual/best-effort/Stop
      continuation events as ledger-visible but unconfirmed until exact
      Odylith Markdown appears in the assistant message, and status renders
      Teaser diagnostic, Ambient, Observation/Proposal, and Assist visibility
      ratios instead of hiding family gaps behind one aggregate count.
- [x] Add a shared transcript-replay read model for true chat visibility.
      Pending hidden, manual-visible, best-effort, and Stop-continuation
      blocks now remain replayable until exact assistant transcript
      confirmation, with missing live rulers repaired, Assist kept outside the
      live ruler, and prompt/checkpoint fallback, `visible-intervention`,
      `intervention-status`, and Stop all consuming the same replay primitive.
- [x] Harden v0.1.10 to v0.1.11 ledger migration behavior: future visible
      fallback events carry explicit host/session envelope fields, legacy
      visible rows infer host family from `render_surface`, and exact assistant
      transcript probes can promote fallback-visible events once without
      duplicating confirmations.
- [x] Wire Guidance Behavior Enhancements through the same low-latency evidence
      cone: Context Engine attaches `guidance_behavior_summary` only for
      relevant packets, Execution Engine carries the validator command as
      recommended validation, Memory Contracts preserve the compact summary in
      context/evidence packets, intervention alignment records
      `guidance_behavior_contract` only when material, and the Tribunal-ready
      signal is precomputed without provider calls or repo-wide scans.
- [x] Add a reusable guidance-surface contract check so
      `odylith validate guidance-behavior` also proves Codex, Claude,
      installed skills, command shims, and consumer/dogfood/source-local lane
      guidance are aligned with the same CLI-first validator and quick
      benchmark proof path.
- [x] Add a platform end-to-end contract check so benchmark/eval wiring,
      Codex and Claude skill/command mirrors, bundled consumer assets, and
      install guidance all stay aligned with the same Guidance Behavior proof
      path without running provider calls, repo-wide scans, or full validation
      on live packet hot paths.
- [x] Harden Guidance Behavior bundle parity: the platform contract now fails
      stale live/source-bundle mirrors for guidance docs, host shims, skills,
      governed program/spec truth, and benchmark corpora instead of accepting
      token-present but lane-stale assets.
- [x] Add the `hot_path_efficiency` platform contract domain: Guidance
      Behavior packets now suppress adaptive session/full-scan widening when
      the deterministic validator summary is present, skip runtime projection
      warmup, avoid projection-store opens for no-projection families, avoid
      delivery-intelligence reads for unanchored packets, and defer host
      capability probes until a route-ready delegate path can actually use
      them.

## Defer
- [ ] User-selectable voice packs or per-repo voice overrides.
- [ ] Per-surface proposal approval instead of one bundle confirmation.
- [ ] Auto-applying update, reopen, or review-refresh actions when no safe
      CLI-backed helper exists yet.
- [ ] Broad semantic repo search during hot-path intervention reasoning.
- [ ] Runtime adaptive learning or provider-backed embeddings for signal
      selection. Those require a later governed visibility-governor layer and
      real adjudicated data density.
- [ ] Any public claim that the visible signal selector is ML-calibrated while
      corpus quality remains `bootstrap`.

## Success Criteria
- [x] The shared engine produces the same structured observation/proposal
      bundle for the same observation envelope on Codex and Claude.
- [x] Prompt-only evidence yields at most a teaser; corroborated evidence can
      produce one rich `Odylith Observation`; stable governed targets can
      produce one `Odylith Proposal`.
- [x] `stop_summary` can now surface a real `Odylith Observation` before
      proposal readiness is high enough; `Odylith Proposal` is gated later by
      concrete readiness instead of being assembled eagerly on every signal.
- [x] Observation and proposal markdown reads as warm, clear, precise, and
      human rather than mechanical or bureaucratic.
- [x] Voice composition is now deterministic and proposition-native: selected
      facts and action rationales drive the claim, implication, teaser body,
      proposal lead, and proposal bullets while fixed structural wrappers stay
      centralized.
- [x] The engine now uses session-aware escalation and repeat suppression, so
      a forming beat, a corroborated return beat, and a stale repeated beat no
      longer travel through the same selector path.
- [x] The engine now keeps one stable intervention identity across prompt,
      stop, and edit/bash hooks, and it can surface the first eligible
      Proposal without re-announcing an already-rendered Observation.
- [x] Apply and decline now preserve moment metadata as terminal lifecycle
      events, so continuity survives all the way through stale/proposed/applied
      reasoning instead of breaking at the confirmation boundary.
- [x] Observation now renders like `Odylith Assist`: one short labeled line
      with one real insight and one real implication, not a mini report.
- [x] Proposal now renders as a short ruled block with a couple of lines and a
      few compact bullets instead of a full sectioned card.
- [x] The opening Observation line makes the interjection explicit, and the
      shipped Proposal copy stays plain enough that it reads like a helpful
      human suggestion rather than branded filler.
- [x] Duplicate-aware lookup prefers update, reopen, link, or review-refresh
      over creating duplicate Radar, Registry, Atlas, or Casebook truth.
- [x] Proposal apply uses existing CLI-backed helpers only, refreshes touched
      governed surfaces, and records applied or declined state in Compass.
- [x] Observation and proposal markdown survives host rendering and Compass
      event storage without being flattened into single-line summaries.
- [x] Preview-only proposal bundles refuse apply until every action in the
      bundle has a safe CLI-backed lane.
- [x] Later stop-summary and edit-checkpoint hooks continue reasoning from the
      human prompt rather than stale Observation or Proposal summaries.
- [x] Pending proposal state carries rich proposal display payloads and status
      so downstream surfaces can render the same Proposal UX without rebuilding
      it from logs.
- [x] Operators can now ask whether the intervention engine is active in Codex
      or Claude and receive one compact Markdown status with readiness checks,
      active UX lanes, recent visible-ready delivery, pending proposal count,
      and a direct `visible-intervention` smoke command.
- [x] High-value distinct ambient propositions can render together under the
      adaptive budget; the cap is not effectively `1`.
- [x] Duplicate visible proposition rate is `0.0` in value-engine unit and
      corpus-report tests.
- [x] Explicit visibility-failure cases have visibility recall `1.0` in the
      bootstrap advisory report.
- [x] Runtime does not load or claim calibrated thresholds while corpus quality
      remains bootstrap.
- [x] Weak, unsupported, stale, contradictory, hidden-only, generated-only,
      mixed non-current evidence, unknown labels, and unknown block kinds
      suppress with precise reasons instead of noisy chat output.
- [x] Label/block-kind mismatches and Proposal restatements suppress before
      they can evade live budgets, proposal dependencies, or duplicate
      accounting.
- [x] Live blocks are canonicalized with top and bottom rulers; Assist remains
      closeout-owned and outside the ruled live block.
- [x] Guidance Behavior Enhancements now feed Context Engine, Execution
      Engine, Memory Contracts, Governance Intervention Engine, Tribunal-ready
      signal shaping, and benchmark validation as one reusable contract instead
      of a detached validator.
- [x] Guidance Behavior Enhancements now also feed host and lane guidance:
      Codex `spawn_agent` prompts, Claude Task-tool subagents, consumer
      installed skills, pinned dogfood, and source-local maintainer mode all
      converge on the same validator command and bounded-delegation fields.
- [x] Guidance Behavior platform proof now covers benchmark/eval integration,
      host skill and command mirrors, consumer bundle assets, and install
      guidance through `odylith_guidance_behavior_platform_end_to_end.v1`.
- [x] Chatter, Compass, host contracts, Registry specs, Atlas, and maintainer
      guidance all describe the same observation/proposal UX and voice rules.
- [x] Agent guidance now explicitly forbids demoing Observation or Proposal UX
      to humans as fenced raw Markdown unless the task is specifically about
      debugging raw Markdown rendering.
- [x] Demo and fixture copy is now governed as well: mockups should use
      concrete governed meaning, not decorative filler text.
- [x] Compass proposal summaries and pending rows no longer need to fall back
      to self-referential placeholders such as `Odylith Proposal pending.`;
      the event stream can carry human useful proposal summaries directly.
- [x] Prompt-submit teasers now use the strongest available surface for each
      host: Codex uses structured `systemMessage` plus assistant-render
      fallback context, while Claude splits `prompt-context` from
      `prompt-teaser` so discreet anchor continuity, best-effort stdout, and
      assistant-render fallback all survive.
- [x] Claude `PostToolUse` edit checkpoints now stay synchronous so earned
      Observations and Proposals are not delayed into hidden or next-turn
      async reminders.
- [x] Codex `PostToolUse` checkpoint matching now covers `Bash`, native
      `apply_patch`, and command-style exec payloads, and the checkpoint parser
      can recover patch paths from native apply-patch hook payloads before
      building the visible Observation/Proposal beat.
- [x] Source-bundle packaging now carries the intervention host/spec guidance
      and command-skill shims, while Compass runtime state is stripped from the
      shipped install bundle instead of leaking a maintainer repo snapshot.
- [x] Registry and Radar validation caches now carry the Radar idea parser
      contract version, so stale cached `idea-parse` diagnostics cannot block
      valid component-registry validation after parser-shape changes.
- [x] Focused runtime tests and governance validators pass on the touched
      slice.

## Non-Goals
- [ ] Turning Odylith into a constant interrupting copilot that comments on
      every turn.
- [ ] Shipping a configurable voice-pack surface in this release.
- [ ] Replacing Radar, Registry, Atlas, or Casebook ownership with an
      intervention-local shadow record.
- [ ] Adding broad fresh-search dependencies to the hot path just to make the
      copy sound impressive.

## Impacted Areas
- [ ] [2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md)
- [ ] [2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md)
- [ ] [src/odylith/runtime/intervention_engine/](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine)
- [ ] [src/odylith/runtime/intervention_engine/conversation_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/conversation_runtime.py)
- [ ] [value_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/value_engine.py)
- [ ] [value_engine_types.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/value_engine_types.py)
- [ ] [value_engine_selection.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/value_engine_selection.py)
- [ ] [value_engine_corpus.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/value_engine_corpus.py)
- [ ] [value_engine_migration.py](/Users/freedom/code/odylith/src/odylith/install/value_engine_migration.py)
- [ ] [odylith_intervention_value_engine_benchmark.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_intervention_value_engine_benchmark.py)
- [ ] [intervention-value-adjudication-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/intervention-value-adjudication-corpus.v1.json)
- [ ] [src/odylith/runtime/surfaces/](/Users/freedom/code/odylith/src/odylith/runtime/surfaces)
- [ ] [src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [ ] [odylith/registry/source/components/](/Users/freedom/code/odylith/odylith/registry/source/components)
- [ ] [odylith/atlas/source/](/Users/freedom/code/odylith/odylith/atlas/source)
- [ ] [odylith-conversation-observation-and-governed-proposal-flow.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-conversation-observation-and-governed-proposal-flow.mmd)
- [ ] [odylith/agents-guidelines/](/Users/freedom/code/odylith/odylith/agents-guidelines)
- [ ] [odylith/maintainer/AGENTS.md](/Users/freedom/code/odylith/odylith/maintainer/AGENTS.md)
- [ ] [odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md](/Users/freedom/code/odylith/odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md)
- [ ] [AGENTS.md](/Users/freedom/code/odylith/AGENTS.md)
- [ ] [src/odylith/install/agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [ ] [tests/unit/runtime/](/Users/freedom/code/odylith/tests/unit/runtime)
- [ ] [guidance_behavior_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/guidance_behavior_runtime.py)
- [ ] [guidance_behavior_runtime_contracts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/guidance_behavior_runtime_contracts.py)
- [ ] [guidance_behavior_guidance_contracts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/guidance_behavior_guidance_contracts.py)
- [ ] [guidance_behavior_platform_contracts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/guidance_behavior_platform_contracts.py)
- [ ] [guidance_behavior_benchmark_contracts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/guidance_behavior_benchmark_contracts.py)
- [ ] [validate_guidance_behavior.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/validate_guidance_behavior.py)
- [ ] [guidance-behavior-evaluation-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json)
- [ ] [odylith-guidance-behavior skill](/Users/freedom/code/odylith/odylith/skills/odylith-guidance-behavior/SKILL.md)
- [ ] [Codex guidance behavior skill shim](/Users/freedom/code/odylith/.agents/skills/odylith-guidance-behavior/SKILL.md)
- [ ] [Claude guidance behavior command](/Users/freedom/code/odylith/.claude/commands/odylith-guidance-behavior.md)
- [ ] [alignment_evidence.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/alignment_evidence.py)

## Rollout
1. Bind `B-096` and child waves `B-105` through `B-109` to v0.1.11.
2. Land the shared intervention-engine runtime, value engine, migration, and
   CLI wrappers.
3. Wire host hooks, Chatter bundle carry-through, and Compass pending proposal
   derivation.
4. Harden apply behavior around deterministic CLI-backed governed creates and
   preview-only update paths.
5. Update Registry specs, Atlas topology, host guidance, and maintainer voice
   guidance in the same change.
6. Run focused validation, then refresh only the impacted governed surfaces.

## Cross-Lane Impact
- **dev-maintainer (`source-local`)**: this is the primary execution lane for
  proving the new runtime package and hook integrations before release.
- **pinned dogfood**: receives the observation/proposal UX only once the
  shipped runtime includes the shared engine, CLI wrappers, and host wiring.
- **consumer pinned-runtime**: gains the experience on upgrade; the guidance
  and voice contract must stay stable enough that the shipped product does not
  suddenly sound mechanical in downstream repos.
- Guidance Behavior proof must work in all three lanes: source-local proves the
  unreleased validator and benchmark, pinned dogfood proves the shipped
  runtime, and consumer pinned-runtime receives the same command/skill guidance
  through installed bundle assets.

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_claude_host_prompt_context.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_odylith_assist_closeout.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_claude_host_stop_summary.py tests/unit/test_cli.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine_apply.py tests/unit/runtime/test_intervention_engine_performance.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_intervention_engine_apply.py tests/unit/runtime/test_intervention_engine_performance.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_claude_host_stop_summary.py tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/test_cli.py`
- [x] Manual lifecycle eval: prompt memory persists through emitted intervention
      events and pending proposal state still exposes markdown/status payloads
      for downstream rendering.
- [x] `./.odylith/bin/odylith validate backlog-contract --repo-root .`
- [x] `./.odylith/bin/odylith governance validate-plan-traceability --repo-root .`
- [x] `./.odylith/bin/odylith validate component-registry --repo-root .`
- [x] `./.odylith/bin/odylith atlas refresh --repo-root . --atlas-sync`
- [x] `./.odylith/bin/odylith registry refresh --repo-root .`
- [x] `./.odylith/bin/odylith radar refresh --repo-root .`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_component_registry_intelligence.py tests/unit/runtime/test_validate_component_registry_contract.py` (`47 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_host_surface_runtime.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_intervention_cross_host_parity.py tests/unit/runtime/test_host_hook_cli_dispatch.py tests/unit/install/test_codex_project_assets.py tests/unit/test_claude_project_hooks.py tests/unit/test_codex_host_cli.py tests/unit/test_claude_host_cli.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_component_registry_intelligence.py tests/unit/runtime/test_validate_component_registry_contract.py` (`143 passed`)
- [x] `git diff --check`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_intervention_engine_apply.py tests/unit/runtime/test_intervention_engine_performance.py tests/unit/runtime/test_intervention_conversation_surface.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_intervention_cross_host_parity.py tests/unit/runtime/test_intervention_host_surface_runtime.py tests/unit/runtime/test_host_hook_cli_dispatch.py tests/unit/runtime/test_claude_host_post_edit_checkpoint.py tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_claude_host_stop_summary.py tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/install/test_claude_effective_settings.py tests/unit/install/test_codex_project_assets.py tests/unit/test_cli.py tests/unit/test_cli_audit.py tests/unit/test_claude_host_cli.py tests/unit/test_codex_host_cli.py` (`367 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/install/test_manager.py` (`78 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_surface_shell_contracts.py tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_component_registry_intelligence.py tests/unit/runtime/test_validate_backlog_contract.py` (`191 passed`)
- [x] Source CLI selective `odylith sync --impact-mode selective --proceed-with-overlap ...` completed after removing unlinked manual smoke-only Compass card events and refreshing Radar, Registry, Atlas, Casebook, and Compass surfaces.
- [x] Direct host-output smoke proves structured hook generation, not chat visibility by itself: Claude `prompt-context` emits discreet JSON context with assistant-render fallback, Claude `prompt-teaser` emits best-effort plain stdout, Claude checkpoints emit `systemMessage` plus fallback context, and Codex Bash checkpoints emit `systemMessage` plus fallback context.
- [x] Claude compatibility reporting now names both prompt seams explicitly: `UserPromptSubmit prompt-context hook wired: yes` and `UserPromptSubmit prompt-teaser hook wired: yes`.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_codex_host_compatibility.py tests/unit/install/test_codex_project_assets.py tests/unit/runtime/test_host_runtime_contract.py` (`37 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_host_surface_runtime.py tests/unit/runtime/test_intervention_cross_host_parity.py tests/unit/runtime/test_host_hook_cli_dispatch.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_claude_host_compatibility.py tests/unit/install/test_claude_effective_settings.py` (`37 passed`)
- [x] Codex native `apply_patch` payload parsing remains covered for manual/test fallback, but current Codex hook schema exposes `PostToolUse` for `Bash` only. Chat visibility now relies on assistant-render fallback context, one-shot Stop continuation for missed Assist/Observation closeout, and the shared `visible-intervention` command instead of claiming native desktop tool hooks are automatically dispatched.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_host_surface_runtime.py tests/unit/runtime/test_host_visible_intervention.py tests/unit/runtime/test_codex_host_prompt_context.py tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_intervention_cross_host_parity.py tests/unit/runtime/test_host_hook_cli_dispatch.py tests/unit/runtime/test_codex_host_compatibility.py tests/unit/runtime/test_claude_cli_capabilities.py tests/unit/runtime/test_claude_host_compatibility.py tests/unit/runtime/test_host_runtime_contract.py tests/unit/install/test_codex_project_assets.py tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_claude_host_stop_summary.py` (`85 passed`)
- [x] Stop-summary Assist now recovers from concrete validation/pass signals in
      the assistant summary when changed paths are unavailable, without
      claiming artifact updates. Codex and Claude `visible-intervention`
      smokes both render the same `**Odylith Assist:**` line from that proof
      path.
- [x] Stop-summary Assist now carries bounded `affected_contracts` and renders
      the governed workstream, component, diagram, or bug IDs involved in the
      closeout. It says `updating` only when governed changed paths prove a
      write and otherwise says the proof stayed inside affected contracts.
- [x] Ambient surfacing now has its own checkpoint/stop recovery lane and wins
      over stale teaser text once the signal has matured, while prompt submit
      stays teaser-only.
- [x] Stop-summary Assist now recovers from explicit Odylith visibility
      feedback even when the last assistant message is too short to be a
      meaningful implementation summary. Ordinary low-signal short turns still
      suppress Assist.
- [x] Stop visible-delivery dedupe now matches the generated Odylith labels
      instead of suppressing a closeout just because any prior Odylith label
      appeared.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_conversation_surface.py tests/unit/runtime/test_intervention_host_surface_runtime.py tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_claude_host_stop_summary.py tests/unit/runtime/test_intervention_delivery_status.py` (`71 passed`)
- [x] Stop now replays the bounded distinct set of unseen Ambient Highlight,
      Observation, and Proposal blocks from the session event stream before
      Assist, using the same one-shot continuation path that made Assist
      visible.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_host_surface_runtime.py tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_claude_host_stop_summary.py` (`39 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_value_engine.py tests/unit/runtime/test_intervention_value_engine_benchmark.py tests/unit/install/test_value_engine_migration.py` (`12 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_conversation_surface.py tests/unit/runtime/test_host_visible_intervention.py tests/unit/runtime/test_intervention_visibility_broker.py tests/unit/runtime/test_intervention_host_surface_runtime.py` (`58 passed`)
- [x] After decomposing `value_engine.py`, `PYTHONPATH=src python3 -m
      py_compile src/odylith/runtime/intervention_engine/value_engine.py
      src/odylith/runtime/intervention_engine/value_engine_types.py
      src/odylith/runtime/intervention_engine/value_engine_selection.py
      src/odylith/runtime/intervention_engine/value_engine_corpus.py
      src/odylith/runtime/intervention_engine/conversation_surface.py
      src/odylith/runtime/evaluation/odylith_intervention_value_engine_benchmark.py
      src/odylith/install/value_engine_migration.py src/odylith/install/manager.py`
      passed.
- [x] `PYTHONPATH=src python3 -m pytest -q
      tests/unit/runtime/test_intervention_value_engine.py
      tests/unit/runtime/test_intervention_value_engine_benchmark.py
      tests/unit/install/test_value_engine_migration.py
      tests/unit/runtime/test_intervention_conversation_surface.py
      tests/unit/runtime/test_host_visible_intervention.py
      tests/unit/runtime/test_intervention_visibility_broker.py
      tests/unit/runtime/test_intervention_host_surface_runtime.py` (`70 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q
      tests/unit/runtime/test_validate_backlog_contract.py
      tests/unit/runtime/test_validate_component_registry_contract.py
      tests/unit/runtime/test_component_registry_intelligence.py
      tests/unit/runtime/test_render_mermaid_catalog.py
      tests/unit/runtime/test_auto_update_mermaid_diagrams.py` (`84 passed`)
- [x] `odylith validate backlog-contract --repo-root .`,
      `odylith validate component-registry --repo-root .`,
      `odylith validate casebook-source --repo-root .`, and
      `odylith atlas render --repo-root . --check-only --diagram-id D-038
      --runtime-mode standalone` passed.
- [x] `odylith sync --repo-root . --force --runtime-mode standalone
      --proceed-with-overlap` passed, followed by `odylith sync --repo-root .
      --check-only --runtime-mode standalone` and `git diff --check`.
- [x] Proposition-native voice hardening validation:
      `python -m py_compile src/odylith/runtime/intervention_engine/voice.py
      src/odylith/runtime/surfaces/codex_host_stop_summary.py
      src/odylith/runtime/surfaces/claude_host_stop_summary.py
      tests/unit/runtime/test_intervention_voice.py` passed.
- [x] Proposition-native voice focused regression:
      `pytest -q tests/unit/runtime/test_intervention_voice.py
      tests/unit/runtime/test_intervention_engine.py
      tests/unit/runtime/test_intervention_conversation_surface.py
      tests/unit/runtime/test_codex_host_prompt_context.py
      tests/unit/runtime/test_claude_host_prompt_context.py
      tests/unit/runtime/test_codex_host_stop_summary.py
      tests/unit/runtime/test_claude_host_stop_summary.py
      tests/unit/runtime/test_intervention_cross_host_parity.py
      tests/unit/runtime/test_intervention_engine_performance.py
      tests/unit/runtime/test_intervention_host_surface_runtime.py
      tests/unit/runtime/test_host_visible_intervention.py
      tests/unit/runtime/test_host_hook_cli_dispatch.py
      tests/unit/runtime/test_codex_host_post_bash_checkpoint.py
      tests/unit/runtime/test_claude_host_post_bash_checkpoint.py
      tests/unit/runtime/test_claude_host_post_edit_checkpoint.py`
      (`163 passed`).
- [x] Full runtime unit regression after voice hardening:
      `pytest -q tests/unit/runtime` (`1987 passed`).
- [x] Browser-visible and install/guidance regression after voice hardening:
      `pytest -q tests/integration/runtime/test_intervention_visibility_browser.py
      tests/integration/install/test_manager.py tests/unit/install/test_agents.py`
      (`88 passed`).
- [x] Visibility accounting regression after ledger-proof tightening:
      `python3 -m py_compile
      src/odylith/runtime/intervention_engine/delivery_ledger.py
      src/odylith/runtime/surfaces/host_intervention_status.py
      src/odylith/runtime/intervention_engine/alignment_context.py
      src/odylith/runtime/intervention_engine/visibility_broker.py
      src/odylith/runtime/intervention_engine/host_surface_runtime.py`
      passed, and `PYTHONPATH=src python3 -m pytest -q
      tests/unit/runtime/test_intervention_delivery_status.py
      tests/unit/runtime/test_host_visible_intervention.py
      tests/unit/runtime/test_intervention_visibility_broker.py
      tests/unit/runtime/test_intervention_host_surface_runtime.py`
      (`57 passed`).
- [x] Governance/browser proof after strict transcript-vs-ledger split:
      `PYTHONPATH=src python3 -m odylith.cli sync --repo-root .
      --check-only --runtime-mode standalone --proceed-with-overlap ...`
      passed after refreshing Registry forensics, Atlas freshness, and delivery
      intelligence; `PYTHONPATH=src python3 -m pytest -q
      tests/integration/runtime/test_intervention_visibility_browser.py`
      (`4 passed`); `git diff --check` passed.
- [x] Reuse hardening: extracted shared visibility semantics into
      `src/odylith/runtime/intervention_engine/visibility_contract.py` and
      rewired the delivery ledger, visibility broker, alignment context,
      `intervention-status`, and ambient dedupe to use the same host-family,
      visible-family, ledger-visible, chat-confirmed, pending-confirmation,
      and proof-status contract. Focused regression:
      `PYTHONPATH=src python3 -m pytest -q
      tests/unit/runtime/test_visibility_contract.py
      tests/unit/runtime/test_intervention_delivery_status.py
      tests/unit/runtime/test_host_visible_intervention.py
      tests/unit/runtime/test_intervention_visibility_broker.py
      tests/unit/runtime/test_intervention_host_surface_runtime.py
      tests/unit/runtime/test_intervention_conversation_surface.py`
      (`80 passed`).
- [x] Transcript-replay hardening: added
      `src/odylith/runtime/intervention_engine/visibility_replay.py` and
      rewired prompt submit, post-tool checkpoints, manual visible fallback,
      status, and Stop recovery so unconfirmed branded blocks replay as exact
      assistant-visible Markdown until `assistant_chat_confirmed` is recorded.
      Focused regression:
      `PYTHONPATH=src python3 -m pytest -q
      tests/unit/runtime/test_visibility_contract.py
      tests/unit/runtime/test_visibility_replay.py
      tests/unit/runtime/test_intervention_delivery_status.py
      tests/unit/runtime/test_intervention_host_surface_runtime.py
      tests/unit/runtime/test_host_visible_intervention.py
      tests/unit/runtime/test_codex_host_prompt_context.py
      tests/unit/runtime/test_claude_host_prompt_context.py
      tests/unit/runtime/test_codex_host_post_bash_checkpoint.py
      tests/unit/runtime/test_claude_host_post_bash_checkpoint.py
      tests/unit/runtime/test_claude_host_post_edit_checkpoint.py
      tests/unit/runtime/test_codex_host_stop_summary.py
      tests/unit/runtime/test_claude_host_stop_summary.py
      tests/unit/runtime/test_intervention_visibility_broker.py`
      (`141 passed`).
- [x] Guidance Behavior end-to-end integration proof:
      `odylith validate guidance-behavior --repo-root . --json` passed,
      `py_compile` passed for the touched
      guidance/context/execution/memory/intervention modules, and focused
      runtime regression over guidance behavior, packet summaries, execution
      handshakes, memory contracts, intervention alignment evidence,
      visibility broker/performance, CLI, sync compatibility, and benchmark
      isolation passed (`326 passed`).
- [x] Guidance Behavior guidance-surface hardening proof:
      `odylith validate guidance-behavior --repo-root . --json` passed with
      `6` cases, `11` guidance checks,
      `0` failed check ids, and critical/high severity counts preserved;
      the new platform end-to-end check proved `benchmark_eval`,
      `host_lane_bundle_mirrors`, and `hot_path_efficiency` domains plus
      live/source-bundle byte parity for the shipped guidance surfaces;
      `odylith benchmark --repo-root . --profile quick --family
      guidance_behavior --no-write-report --json` selected only
      `guidance_behavior`, ran `6` scenarios, and cleared the hard gate;
      focused validator/install/benchmark regression passed
      (`224 passed`).
- [x] Guidance Behavior hot-path efficiency proof:
      `odylith benchmark --repo-root . --profile quick --family
      guidance_behavior --no-write-report --json` selected `6` guidance
      scenarios, used only `impact` packets for Odylith ON, reported
      `odylith_requires_widening_rate=0.0`, cleared hard and secondary
      guardrails with no advisory failures, and measured Odylith ON packet
      timing at `median=5.712 ms`, `avg=5.999 ms`, `p95=7.463 ms`.
