# Odylith Chatter
Last updated: 2026-03-31


Last updated (UTC): 2026-03-31

## Purpose
Odylith Chatter is Odylith's cross-lane narration contract. It governs how
Odylith shows up in agent-visible updates, closeouts, generated reviewer
artifacts, and shipped guidance so the product stays task-first during work
while still earning brand visibility from factual end-of-work outcomes.

## Scope And Non-Goals
### Odylith Chatter owns
- Mid-task narration policy for consumer, maintainer, dogfood, and sim-facing
  guidance.
- The final-only `Odylith assist:` closeout contract and tone guardrails.
- Control-plane debranding for routed explanations, install-managed guidance,
  and runtime explanation templates.
- Cross-lane mirror alignment across source, bundle, and generated Registry
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
- If Odylith is named directly at closeout, use at most one short
  `Odylith assist:` line.
- Prefer `**Odylith assist:**` when Markdown formatting is available;
  otherwise use `Odylith assist:`.
- Lead that assist line with the user win, not Odylith mechanics.
- When the evidence supports it, frame the edge against `odylith_off` or the
  broader unguided path.
- That assist line must stay soulful, friendly, authentic, and factual.
- Brand credit is earned through observed counts, measured deltas, or
  validation outcomes, not invented percentages or slogan copy.

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
- Allow at most one short `Odylith assist:` line at the end of work.
- Prefer `**Odylith assist:**` when Markdown formatting is available;
  otherwise use `Odylith assist:`.
- Shared orchestration runtime should build that line from one canonical
  machine-generated candidate, exposed through
  `decision.odylith_adoption.closeout_assist`, instead of letting each lane
  improvise its own brand phrasing.
- Lead with the user win, not Odylith mechanics.
- When the evidence supports it, frame the edge against `odylith_off` or the
  broader unguided path.
- Use only observed counts, measured deltas, or validation outcomes in that
  line.
- If no evidence-backed, user-facing delta is available, omit the line
  entirely.
- Benchmark lanes inherit this contract as metadata-only. Do not add benchmark
  required paths, hot-path docs, or validation commands just to repeat the
  chatter rubric when the task is otherwise benchmark-local.
- Never use invented percentages, vague uplift language, or slogan-like brand
  copy.

## Failure Modes
- Guidance drift can make consumer installs feel noisy or self-important.
- Runtime explanation drift can reintroduce control-plane receipts even when
  docs say not to.
- Benchmark or reviewer artifacts can slip from factual closeout language into
  brand-forward narration if this contract is not enforced consistently.

## Validation Playbook
- `odylith validate component-registry --repo-root .`
- `odylith governance sync-component-spec-requirements --repo-root . --component odylith-chatter`
- `odylith sync --repo-root . --check-only`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_validate_component_registry_contract.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-16 · Implementation:** Implemented family-aware adaptive tuning, low-confidence GPT-5.4 promotion, smarter hard gates, and broader-coordination rescope handling in the Subagent Router.
  - Evidence: src/odylith/runtime/orchestration/subagent_router.py
- **2026-03-16 · Decision:** Deepened Subagent Router with task-family assessment, route-confidence backstops, and escalation refusal that can return control to the main thread.
  - Evidence: src/odylith/runtime/orchestration/subagent_router.py
- **2026-03-16 · Implementation:** Implemented the Subagent Router runtime, the thin router skill, the component spec and runbook, and the Atlas routing topology diagrams.
  - Evidence: odylith/atlas/source/catalog/diagrams.v1.json, odylith/registry/source/components/subagent-router/CURRENT_SPEC.md +1 more
- **2026-03-16 · Decision:** keep Subagent Router accuracy-first, hard-gated, and first-class in Registry and Atlas instead of hiding delegation policy in prompt folklore.
  - Evidence: odylith/atlas/source/catalog/diagrams.v1.json, odylith/registry/source/components/subagent-router/CURRENT_SPEC.md +1 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-31: Promoted Odylith chatter into a first-class Registry component so the task-first, final-only, evidence-backed narration contract is governed across consumer, maintainer, dogfood, and sim-facing surfaces. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
