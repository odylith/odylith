# Odylith Chatter
Last updated: 2026-04-09


Last updated (UTC): 2026-04-07

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
- Ambient `Odylith Insight:`, `Odylith History:`, and `Odylith Risks:`
  candidates plus their suppression and selection rules.
- The final `Odylith Assist:` closeout contract, including the rule to link
  updated governance ids inline when they were actually changed, plus tone
  guardrails.
- Benchmark-safe consumption of precomputed Tribunal-backed delivery signals
  when those signals sharpen ambient narration without requiring a live
  diagnosis pass.
- Control-plane debranding for routed explanations, install-managed guidance,
  and runtime explanation templates.
- Cross-surface mirror alignment across source, bundle, and generated Registry
  surfaces for this narration policy.

### Odylith Chatter does not own
- Grounding, routing, or orchestration decisions themselves.
- Benchmark deltas or validation outcomes beyond how those facts may be named
  in the final closeout line.
- Operator-facing CLI command semantics.

## Developer Mental Model
- During work, Odylith should be doing real grounding and agentic execution in
  the background without making the user read control-plane receipts.
- Mid-task updates stay task-first: describe scope, progress, blockers, and
  evidence, not startup chatter or fallback mechanics, unless a literal
  command or live blocker matters to the user.
- Ambient intelligence is the default UX: weave Odylith-grounded facts into
  ordinary commentary when they change the next move.
- The strongest ambient beats should prefer already-available Tribunal-backed
  diagnosis when the packet or precomputed delivery payload already knows the
  scenario, case queue, proof routes, or systemic causes.
- Explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels
  should feel rare and earned. Pick the strongest one or stay quiet.
- If Odylith is named directly at closeout, use at most one short
  `Odylith Assist:` line plus at most one supplemental closeout line.
- Prefer `**Odylith Assist:**` when Markdown formatting is available;
  otherwise use `Odylith Assist:`.
- Lead that assist line with the user win, not Odylith mechanics, and link
  updated governance ids inline when they were actually changed.
- When the evidence supports it, frame the edge against `odylith_off` or the
  broader unguided path.
- Odylith's voice should stay crisp, authentic, clear, simple, insightful,
  erudite in thought, soulful, friendly, free-flowing, human, and factual.
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
- `odylith/skills/delivery-governance-surface-ops/SKILL.md`
- `odylith/skills/odylith-context-engine-operations/SKILL.md`
- `odylith/skills/session-context/SKILL.md`
- `odylith/skills/subagent-orchestrator/SKILL.md`
- `odylith/skills/subagent-router/SKILL.md`

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
- `src/odylith/runtime/orchestration/odylith_chatter_runtime.py`
- `src/odylith/runtime/orchestration/subagent_orchestrator_runtime_signals.py`
- `src/odylith/runtime/orchestration/subagent_router.py`
- `src/odylith/runtime/orchestration/subagent_router_assessment_runtime.py`
- `src/odylith/runtime/orchestration/subagent_router_runtime_policy.py`
  Human-readable routed explanations and runtime closeout phrasing must stay
  debranded during execution.

## Closeout Policy
- Hide Odylith-by-name narration during active execution unless the user
  explicitly asks for a command, a real blocker requires it, or a runtime
  boundary must be surfaced.
- Allow at most one short `Odylith Assist:` line at the end of work.
- Prefer `**Odylith Assist:**` when Markdown formatting is available;
  otherwise use `Odylith Assist:`.
- Shared orchestration runtime should expose one structured closeout bundle and
  preserve `decision.odylith_adoption.closeout_assist` for compatibility
  instead of letting each lane improvise its own brand phrasing.
- Lead with the user win, not Odylith mechanics.
- Link updated governance ids inline when the final changed paths prove those
  records really moved.
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
- Runtime-owned conversation bundles should expose ambient `insight`,
  `history`, and `risks` candidates separately from closeout text.
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
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_odylith_benchmark_corpus.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
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
- **2026-03-16 · Implementation:** Implemented the Subagent Router runtime, the thin router skill, the component spec and runbook, and the Atlas routing topology diagrams.
  - Evidence: odylith/atlas/source/catalog/diagrams.v1.json, odylith/registry/source/components/subagent-router/CURRENT_SPEC.md +1 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-31: Promoted Odylith chatter into a first-class Registry component so the task-first, final-only, evidence-backed narration contract is governed across consumer, maintainer, dogfood, and sim-facing surfaces. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-06: Expanded the chatter contract from a closeout-only note into ambient conversation intelligence with rare labeled `Odylith Insight:`, `Odylith History:`, and `Odylith Risks:` beats plus capitalized `Odylith Assist:` closeout lines that link updated governance ids inline when they were actually changed. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Tightened the runtime contract so closeout narration suppresses overlapping assist/supplement beats and avoids leaning on one small set of stock delta phrases across unrelated governed slices. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Extended the ambient contract so chatter may consume precomputed Tribunal-backed delivery truth for stronger insight, history, and risk beats, while keeping Tribunal out of the live narration hot path and benchmark lanes metadata-only. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Wired ambient chatter to cached delivery-intelligence scope signals and systemic brief data when governed anchors exist, while keeping no-anchor turns on the old zero-extra-work path. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Hardened Tribunal-fed chatter so explicit and cached payloads are normalized before narration, malformed signal shapes degrade quietly, and supplemental closeout lines cannot appear without an `Odylith Assist:` line. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-07: Tightened the hot path so one conversation-bundle pass reuses the same request metrics and context-artifact scan across ambient and closeout composition instead of rescanning the same packet inside closeout. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
