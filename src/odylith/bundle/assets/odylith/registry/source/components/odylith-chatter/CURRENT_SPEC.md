# Odylith Chatter

## Odylith Discipline Contract
- Chatter owns closeout Voice. `Odylith Assist` remains evidence-backed and
  human; Odylith Discipline closeout language must not become mechanical compliance
  copy or claim completion beyond fresh proof.
- Odylith Discipline signals may inform closeout only after proof, benchmark, or
  visible-intervention evidence supports the statement.
Last updated: 2026-04-18


Last updated (UTC): 2026-04-17

## Purpose
Odylith Chatter is Odylith's cross-posture narration contract. It governs how
Odylith shows up in agent-visible updates, closeouts, generated reviewer
artifacts, and shipped guidance so the product stays task-first during work,
ambiently helpful in the middle, and earns brand visibility from factual
end-of-work outcomes instead of canned self-promotion.

## Scope And Non-Goals
### Odylith Chatter owns
- Mid-task narration policy for consumer, maintainer, dogfood, and sim-facing
  guidance.
- The broader narration policy around when Odylith should stay ambient,
  task-first, and human instead of sounding like a control-plane receipt.
- The closeout-side consumption contract for carried intervention payloads.
- The final `Odylith Assist:` closeout contract, including the rule to link
  updated governance IDs inline when they were actually changed, name affected
  governance-contract IDs when the slice stayed inside known truth, and keep
  tone guardrails intact.
- The rule that `Odylith Assist` is closeout-owned and must not be wrapped in
  the live ruled Ambient/Observation/Proposal block. Assist may follow live
  recovery, but it is not selected by the value engine's live-block budget.
- Benchmark-safe consumption of precomputed Tribunal-backed delivery signals
  when those signals sharpen ambient narration without requiring a live
  diagnosis pass.
- Control-plane debranding for routed explanations, install-managed guidance,
  and runtime explanation templates.
- Cross-surface mirror alignment across source, bundle, and generated Registry
  surfaces for this narration policy.
- Structured `presentation_policy` carry-through from packets so task-first
  narration, routing-receipt suppression, and surface-fast-lane behavior stay
  driven by explicit runtime policy instead of prose heuristics.

### Odylith Chatter does not own
- Grounding, routing, or orchestration decisions themselves.
- Fact selection, dedupe, or proposal assembly for observation/proposal
  moments; that belongs to
  [Governance Intervention Engine](../governance-intervention-engine/CURRENT_SPEC.md).
- Proposition expected-value scoring, duplicate collapse, live-block budget,
  or visibility proof. Chatter consumes the carried result only at closeout.
- The live mid-turn teaser, Observation, Proposal, and explicit intervention
  surfacing path inside Codex and Claude hooks; that now belongs to
  [Governance Intervention Engine](../governance-intervention-engine/CURRENT_SPEC.md)
  so the hot path stays cheap and consistent.
- Benchmark deltas or validation outcomes beyond how those facts may be named
  in the final closeout line.
- Operator-facing CLI command semantics.

## Developer Mental Model
- During work, Odylith should be doing real grounding and agentic execution in
  the background without making the user read control-plane receipts.
- Mid-task updates stay task-first: describe scope, progress, blockers, and
  evidence, not startup chatter or fallback mechanics, unless a literal
  command or live blocker matters to the user.
- Packet-driven commentary should honor structured `presentation_policy`
  fields such as `commentary_mode`, `suppress_routing_receipts`, and
  `surface_fast_lane`.
- Ambient intelligence is the default UX: weave Odylith-grounded facts into
  ordinary commentary when they change the next move.
- When the shared intervention engine escalates into teaser, Observation, or
  Proposal, the markdown should still feel like Odylith speaking naturally,
  not like a generic alert component with Odylith pasted into the title bar.
- Chatter is no longer the hot path for those live mid-turn beats. That split
  is deliberate: intervention owns the fast path, chatter owns the broader
  narration posture and the final Assist closeout.
- Continuity for teaser, Observation, and Proposal also belongs to the
  intervention engine. Chatter should consume the carried payload, not invent
  a second notion of whether the same moment is fresh, repeated, or ready to
  upgrade.
- Observation and proposal moments must stay rooted in the human conversation.
  If a downstream surface starts narrating from Odylith's own pending/applied
  summary strings instead of the original prompt and evidence, treat that as a
  brand regression and fix the data path rather than polishing the copy.
- The strongest ambient beats should prefer already-available Tribunal-backed
  diagnosis when the packet or precomputed delivery payload already knows the
  scenario, case queue, proof routes, or systemic causes.
- Explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels
  should feel rare and earned. Pick the strongest one or stay quiet.
- If Odylith is named directly at closeout, use at most one short
  `Odylith Assist:` line plus at most one supplemental closeout line.
- Prefer `**Odylith Assist:**` when Markdown formatting is available;
  otherwise use `Odylith Assist:`.
- Lead that assist line with the user win, not Odylith mechanics. Link updated
  governance IDs inline when they were actually changed; if no governed file
  moved, name the affected governance-contract IDs from bounded request or
  packet truth without calling them updated.
- When the evidence supports it, frame the edge against `odylith_off` or the
  broader unguided path.
- Odylith's voice should stay crisp, authentic, clear, simple, insightful,
  erudite in thought, soulful, friendly, free-flowing, human, and factual.
- Observation and proposal blocks should also stay friendly, delightful,
  soulful, insightful, simple, clear, accurate, precise, and human. The
  structure may be governed; the reading experience must not feel templated or
  mechanical.
- Humor or quirk is welcome only when the evidence makes it genuinely funny.
  Silence is better than filler.
- Brand credit is earned through observed counts, measured deltas, validation
  outcomes, or genuinely updated governed truth, not invented percentages,
  vague uplift, or slogan copy.

## Runtime And Guidance Contract
### Source-owned contract surfaces
- `AGENTS.md`
- `odylith/AGENTS.md`
- `odylith/README.md`
- `odylith/agents-guidelines/GROUNDING_AND_NARROWING.md`
- `odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`
- `odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`
- `odylith/agents-guidelines/VALIDATION_AND_TESTING.md`
- `odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md`
- `odylith/skills/odylith-context-engine-operations/SKILL.md`
- `odylith/skills/odylith-session-context/SKILL.md`
- `odylith/skills/odylith-subagent-orchestrator/SKILL.md`
- `odylith/skills/odylith-subagent-router/SKILL.md`

### Maintainer and benchmark mirrors
- `odylith/maintainer/AGENTS.md`
- `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`
- `odylith/maintainer/skills/release-benchmark-publishing/SKILL.md`
- `docs/benchmarks/README.md`
- `docs/benchmarks/METRICS_AND_PRIORITIES.md`
- `docs/benchmarks/REVIEWER_GUIDE.md`
- `odylith/runtime/source/optimization-evaluation-corpus.v1.json`

### Runtime-owned enforcement surfaces
- `src/odylith/install/agents.py`
  Install-managed root and product-lane guidance templates.
- `src/odylith/install/manager.py`
  Install-time asset sync and managed guidance contract.
- `src/odylith/runtime/orchestration/subagent_orchestrator.py`
- `src/odylith/runtime/intervention_engine/conversation_runtime.py`
- `src/odylith/runtime/orchestration/subagent_orchestrator_runtime_signals.py`
- `src/odylith/runtime/orchestration/subagent_router.py`
- `src/odylith/runtime/orchestration/subagent_router_assessment_runtime.py`
- `src/odylith/runtime/orchestration/subagent_router_runtime_policy.py`
  Human-readable routed explanations and runtime closeout phrasing must stay
  debranded during execution.
- `src/odylith/runtime/intervention_engine/voice.py`
  Shared default Observation/Proposal markdown renderer and voice seam.

## Closeout Policy
- Hide Odylith-by-name narration during active execution unless the user
  explicitly asks for a command, a real blocker requires it, or a runtime
  boundary must be surfaced.
- Allow at most one short `Odylith Assist:` line at the end of work.
- Prefer `**Odylith Assist:**` when Markdown formatting is available;
  otherwise use `Odylith Assist:`.
- Shared intervention runtime should expose one structured closeout bundle and
  preserve `decision.odylith_adoption.closeout_assist` as the canonical
  adoption handoff instead of letting each lane improvise its own brand
  phrasing.
- That closeout bundle must also have at least one real host-visible path.
  Codex and Claude stop-summary surfaces may render the shared closeout Assist
  text directly, and checkpoint developer-context bundles may carry the same
  Assist text forward for continuity. Keeping `Odylith Assist:` trapped in
  orchestration summary state is a product bug, not an acceptable fallback.
- When Assist is actually emitted through Stop or a manual visible fallback,
  the intervention delivery ledger may record an `assist_closeout` event with
  delivery metadata. Chatter owns the voice and eligibility of that closeout;
  the intervention engine owns the low-latency visibility proof read model.
- Assist may emit for explicit Odylith visibility-feedback turns even when no
  files changed, if the prompt or assistant summary names the product signal
  and the delivery problem clearly enough to be user-facing evidence. This is
  the humane recovery path for "I do not see the interventions" feedback, not
  a generic encouragement generator.
- Lead with the user win, not Odylith mechanics.
- Link updated governance IDs inline when the final changed paths prove those
  records really moved.
- Name affected governance-contract IDs from bounded request, packet, or
  target-ref truth when no changed path proves an update but the work plainly
  stayed inside those contracts. Do not describe those contracts as updated.
- When the evidence supports it, frame the edge against `odylith_off` or the
  broader unguided path.
- Use only concrete observed counts, measured deltas, or validation outcomes
  plus evidence-backed governance deltas in that line.
- If no evidence-backed, user-facing delta is available, omit the line
  entirely.
- At most one supplemental closeout line may appear, chosen in priority order
  from `Odylith Risks:`, `Odylith Insight:`, or `Odylith History:`.
- A supplemental closeout line is only allowed when an `Odylith Assist:` line
  is also present; never let `Odylith Risks:`, `Odylith Insight:`, or
  `Odylith History:` stand alone at closeout.
- A supplemental closeout line should add a genuinely new beat; if the assist
  line already covered the same refs and same causal point, suppress the
  supplemental instead of echoing it.
- Benchmark lanes inherit this contract as metadata-only. Do not add benchmark
  required paths, hot-path docs, or validation commands just to repeat the
  chatter rubric when the task is otherwise benchmark-local.
- Never use invented percentages, vague uplift language, slogan-like brand
  copy, or obligatory chatter when the signal is weak.

## Ambient Signal Policy
- Runtime-owned conversation bundles may expose ambient `insight`,
  `history`, and `risks` candidates separately from closeout text.
- The same bundle may also carry one structured `intervention_bundle` holding
  an earned `Odylith Observation` and, when confirmed evidence exists, one
  `Odylith Proposal`, but the hook-time live renderer should come from the
  intervention engine fast path rather than forcing every host beat through
  chatter composition.
- Checkpoint hooks may therefore carry two simultaneous surfaces:
  a visible Observation/Proposal beat for the user and a hidden
  Observation/Proposal/Assist developer-context bundle for next-turn
  continuity. Chatter should consume that carried truth instead of trying to
  infer a second visible intervention from the same moment.
- That structured intervention payload should remain the source for the human
  block rendering. Do not rebuild Observation or Proposal UX from Compass event
  summaries when the carried markdown, prompt context, and render policy are
  already available.
- Default render mode is unlabeled ambient weaving inside ordinary task
  commentary.
- Prefer precomputed Tribunal-backed delivery truth over lighter heuristics
  when that stronger diagnosis is already present in packet context or
  precomputed delivery payloads.
- Normalize explicit and precomputed Tribunal-backed chatter payloads before
  narration. Malformed or partial packet truth should degrade to silence or
  lighter heuristics instead of leaking raw structure into the voice.
- Escalate to an explicit `Odylith Insight:` line only when there is a
  non-obvious causal or topology point that changes the next move.
- Escalate to an explicit `Odylith History:` line only when precomputed truth
  shows a strong same-surface, same-component, or same-workstream prior worth
  naming.
- Escalate to an explicit `Odylith Risks:` line only when there is a real
  correctness, release, or governance risk that should interrupt the flow.
- Never emit multiple explicit Odylith labels in one moment.
- Never let one turn render both a stock ambient Odylith label and a full
  `Odylith Observation` block for the same causal point.
- Keep ambient and closeout synthesis benchmark-safe: use already-built packet
  fields, precomputed surface payloads, and the final changed-path list
  supplied to the closeout finalizer. Do not trigger fresh repo search, graph
  rebuild, or semantic retrieval just to narrate Odylith.
- Never invoke live Tribunal or rebuild delivery intelligence just to produce a
  chatter beat. Tribunal belongs in the data path here, not the hot compute
  path.

## Failure Modes
- Guidance drift can make consumer installs feel noisy or self-important.
- Runtime explanation drift can reintroduce control-plane receipts even when
  docs say not to.
- Benchmark or reviewer artifacts can slip from factual closeout language into
  brand-forward narration if this contract is not enforced consistently.
- Ambient signal selection can become repetitive or uncanny if suppression
  rules are weak or exact-sentence snapshots are treated as the real product.
- Closeout can feel fake-smart if `Odylith Assist:` and the supplemental line
  restate the same governed fact in two slightly different stock sentences.
- Observation or proposal markdown can feel uncanny if it keeps the same rigid
  stock cadence across unrelated slices or starts sounding like governance
  paperwork with a brand wrapper.
- Chatter can also cheapen the product if it rebuilds an Observation or
  Proposal from terse stream summaries instead of the carried markdown,
  continuity state, and prompt-rooted payload.
- Tribunal-aware chatter can regress into latency theater if it quietly starts
  a fresh delivery or reasoning pass during ordinary narration.
- Malformed Tribunal-backed payloads can turn one bad packet field into
  character-soup insight text or other uncanny narration if the runtime does
  not normalize the shape first.

## Validation Playbook
- `odylith validate component-registry --repo-root .`
- `odylith governance sync-component-spec-requirements --repo-root . --component odylith-chatter`
- `odylith sync --repo-root . --check-only`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_validate_component_registry_contract.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_intervention_engine.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-04-17 · Implementation:** B-110 Odylith Discipline hardening centralized signal/law policy, ranked open-world affordances, suppressed ephemeral practice refs, tagged Discipline benchmark scenarios to B-110, and proved zero-credit validators plus quick benchmark families with advisory widening at 0.0.
  - Scope: B-110
  - Evidence: odylith/runtime/source/optimization-evaluation-corpus.v1.json, odylith/technical-plans/in-progress/2026-04/2026-04-17-adaptive-agent-operating-character-credit-safe-and-benchmark-proved.md
- **2026-04-07 · Implementation:** Tightened the chatter hot path so one conversation-bundle pass reuses request metrics and context-artifact scans across ambient and closeout composition.
  - Scope: B-031
  - Evidence: odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md, odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md +2 more
- **2026-04-07 · Implementation:** Hardened Tribunal-fed ambient chatter so malformed explicit and cached signal payloads degrade quietly, supplemental closeout lines stay suppressed without an Odylith Assist line, and closeout punctuation stays clean.
  - Scope: B-031
  - Evidence: odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md, odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md +2 more
- **2026-04-05 · Implementation:** Refreshed the benchmark publication story to the April 5 source-local full proof pass 52aa3f76538cf12f: README, benchmark docs, registry spec, plans, and radar now reflect that odylith_on clears the hard gate and secondary guardrails against odylith_off while benchmark_compare still warns until the first shipped release baseline exists.
  - Scope: B-021, B-022
  - Evidence: README.md, docs/benchmarks/README.md +3 more
- **2026-03-16 · Implementation:** Implemented family-aware adaptive tuning, low-confidence GPT-5.4 promotion, smarter hard gates, and broader-coordination rescope handling in the Subagent Router.
  - Evidence: src/odylith/runtime/orchestration/subagent_router.py
- **2026-03-16 · Decision:** Deepened Subagent Router with task-family assessment, route-confidence backstops, and escalation refusal that can return control to the main thread.
  - Evidence: src/odylith/runtime/orchestration/subagent_router.py
<!-- registry-requirements:end -->

## Feature History
- 2026-03-31: Promoted Odylith chatter into a first-class Registry component so the task-first, final-only, evidence-backed narration contract is governed across consumer, maintainer, dogfood, and sim-facing surfaces. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-06: Expanded the chatter contract from a closeout-only note into ambient conversation intelligence with rare labeled `Odylith Insight:`, `Odylith History:`, and `Odylith Risks:` beats plus capitalized `Odylith Assist:` closeout lines that link updated governance ids inline when they were actually changed. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Tightened the runtime contract so closeout narration suppresses overlapping assist/supplement beats and avoids leaning on one small set of stock delta phrases across unrelated governed slices. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Extended the ambient contract so chatter may consume precomputed Tribunal-backed delivery truth for stronger insight, history, and risk beats, while keeping Tribunal out of the live narration hot path and benchmark lanes metadata-only. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Wired ambient chatter to cached delivery-intelligence scope signals and systemic brief data when governed anchors exist, while keeping no-anchor turns on the old zero-extra-work path. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Hardened Tribunal-fed chatter so explicit and cached payloads are normalized before narration, malformed signal shapes degrade quietly, and supplemental closeout lines cannot appear without an `Odylith Assist:` line. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Tightened the hot path so one conversation-bundle pass reuses the same request metrics and context-artifact scan across ambient and closeout composition instead of rescanning the same packet inside closeout. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-10: Bound commentary policy to structured `presentation_policy` fields so consumer and maintainer turns suppress receipts and narrate task-first behavior from the same packet truth. (Plan: [B-082](odylith/radar/radar.html?view=plan&workstream=B-082))
- 2026-04-14: Extended the Chatter contract from ambient commentary and closeout into governed `Odylith Observation` and `Odylith Proposal` rendering, with a future-ready voice seam and an explicit ban on templated or mechanical branded copy. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Hardened the observation/proposal carry-through so prompt-rooted context and rich markdown remain first-class conversation payload, preventing later host or Compass consumers from degrading the UX into self-referential pending-summary narration. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Split the architecture cleanly so live mid-turn teaser/Observation/Proposal rendering runs through the intervention-engine fast path, while Chatter stays responsible for task-first narration policy and the final `Odylith Assist:` closeout. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-14: Clarified that cross-phase moment continuity is intervention-owned too, so Chatter consumes stable carried intervention payloads instead of rebuilding stale or duplicate Observation/Proposal beats from stream summaries. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-16: Linked `Odylith Assist` closeout visibility to the intervention delivery ledger so Codex and Claude can prove Assist was visible-ready without moving Assist voice ownership out of Chatter. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
- 2026-04-16: Extended `Odylith Assist` closeout payloads with affected governance-contract IDs so closeouts can name B-096, component dossiers, diagrams, or bugs even when the final turn only validated within those contracts instead of editing them. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-16: Added the visibility-continuity Assist style so explicit product UX feedback about missing ambient/intervention chat output earns a short human closeout, while ordinary low-signal short turns still suppress Assist. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-121`)
