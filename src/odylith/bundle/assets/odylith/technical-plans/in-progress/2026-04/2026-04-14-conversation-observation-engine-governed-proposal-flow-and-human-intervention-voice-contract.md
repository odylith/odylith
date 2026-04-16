Status: In progress

Created: 2026-04-14

Updated: 2026-04-16

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
- Safe apply in V1 is CLI-first and limited to surfaces where Odylith already
  has deterministic create helpers. Preview may cover richer update or reopen
  paths before apply supports them.
- The advanced fast-path algorithm is two-stage: first a cheap semantic
  prefilter decides whether this turn has governed signal at all; only then
  may repo-truth lookup, dedupe, and proposal assembly run.
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
- No related bug found.

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
      Observation/Proposal UX. Async is fine for background telemetry, but
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

## Defer
- [ ] User-selectable voice packs or per-repo voice overrides.
- [ ] Per-surface proposal approval instead of one bundle confirmation.
- [ ] Auto-applying update, reopen, or review-refresh actions when no safe
      CLI-backed helper exists yet.
- [ ] Broad semantic repo search during hot-path intervention reasoning.

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
- [x] Voice variation is now deterministic by selected moment type, so
      continuation, boundary, guardrail, recovery, and capture moments do not
      all sound like the same branded template.
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

## Rollout
1. Bind `B-096` to this active plan and set the workstream into planning.
2. Land the shared intervention-engine runtime and CLI wrappers.
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
