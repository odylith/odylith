Status: Done

Created: 2026-03-30

Updated: 2026-04-07

Backlog: B-031

Goal: Make Odylith harder for Codex to miss by exposing a short first-turn
grounding path at the top-level CLI and aligning repo-root AGENTS, skills,
guidance, install/on/off messaging, and Odylith's own conversation contract
around that same product posture, including an explicit fallback-to-default-
agent posture when Odylith is intentionally off.

Assumptions:
- The existing Context Engine packet behavior is already strong enough; the
  main gap is discoverability and operator friction.
- `odylith context-engine` should remain the full explicit operator namespace,
  while short-form top-level commands can route to the same implementation.
- Repo-root AGENTS and bundled skills are the highest-leverage places to make
  Odylith-first visible to coding agents.
- `odylith off` should read as an intentional operator choice, not as a broken
  install or ambiguous half-state.

Constraints:
- Do not fork behavior away from the existing Context Engine transport or
  packet semantics.
- Keep install guidance honest: do not imply the short-form bootstrap command
  solves ambiguity that still needs explicit paths or widening.
- Keep source-owned and bundled guidance aligned in the same change.
- Keep conversation synthesis benchmark-safe: use only already-built packet
  fields, precomputed surface payloads, and the final changed-path list
  supplied to the closeout finalizer.
- Do not trigger fresh repo search, graph rebuild, or semantic retrieval just
  to narrate Odylith.
- Treat Tribunal the same way: ambient chatter may consume precomputed
  Tribunal-backed delivery signals, but it must never invoke live Tribunal or
  rebuild delivery intelligence just to sound smarter.

Reversibility: Reverting this slice removes the short-form entrypoints and
restores the previous guidance wording without changing stored runtime state.

Boundary Conditions:
- Scope includes top-level CLI aliases for first-turn grounding, repo-root
  AGENTS activation text, shared and bundled skills/guidance, and install/on
  quickstart messaging.
- Scope excludes Context Engine retrieval-model changes, daemon transport
  changes, and broad shell onboarding redesign.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] The first useful Odylith grounding verbs are still hidden under
      `odylith context-engine ...`.
- [x] Repo-root AGENTS activation still says "use Odylith first" more clearly
      than it says exactly which command to run first.
- [x] Consumer guidance still leaks control-plane chatter into visible agent
      updates instead of keeping Odylith first in the background.
- [x] Shared and bundled skills still teach nested Context Engine commands even
      when a shorter top-level surface would be clearer.
- [x] Install/on messaging does not yet leave operators with one obvious
      first-turn bootstrap path.
- [x] `odylith off` does not yet say plainly that Codex falls back to the
      surrounding repo's default behavior while leaving Odylith installed.
- [x] Ambient and closeout chatter can still feel too stock-sentence-driven
      when different governed slices fall into the same small wording molds.
- [x] A closeout `Odylith Assist:` line and its one allowed supplemental line
      can still echo the same governing beat instead of teaching the user
      something new.

## Success Criteria
- [x] `odylith --help` exposes short-form top-level grounding commands for the
      first-turn happy path.
- [x] Repo-root managed AGENTS text names `odylith bootstrap` plus the next
      narrowing moves explicitly.
- [x] Consumer repo guidance makes substantive Odylith grounding a hard gate,
      keeps the active workstream/component/packet in scope, and allows
      background grounding without a fixed visible commentary prefix.
- [x] Consumer-facing commentary and routed human-readable runtime notes stay
      task-first and avoid control-plane receipts except when an exact command
      or real blocker must be surfaced.
- [x] Mid-task Odylith intelligence stays ambient by default: grounded facts
      get woven into ordinary commentary, while explicit `Odylith Insight:`,
      `Odylith History:`, and `Odylith Risks:` labels stay rare, earned, and
      one-at-a-time.
- [x] Cross-posture closeout guidance allows at most one end-of-work
      `Odylith Assist:` line, preferably `**Odylith Assist:**` when Markdown is
      available, with linked updated governance ids inline and at most one
      supplemental closeout line chosen from `Odylith Risks:`,
      `Odylith Insight:`, or `Odylith History:`.
- [x] A supplemental closeout `Odylith Risks:`, `Odylith Insight:`, or
      `Odylith History:` line never stands alone; if `Odylith Assist:` is
      suppressed, the supplemental closeout line is suppressed too.
- [x] Shared orchestration runtime emits one structured conversation bundle
      with `ambient_signals` and `closeout_bundle`, while keeping
      `decision.odylith_adoption.closeout_assist` backward-compatible.
- [x] Ambient chatter can consume precomputed Tribunal-backed delivery signals
      such as scope scenarios, case refs, proof routes, and systemic-brief
      causes when they are already available, while staying out of the live
      Tribunal hot path.
- [x] Explicit and cached Tribunal-backed chatter payloads get normalized
      before narration so malformed packet truth degrades quietly instead of
      leaking raw structure or character-split noise into the voice.
- [x] Conversation-bundle composition reuses the same precomputed request
      metrics and context-artifact scan across ambient and closeout phases
      instead of rescanning the same packet twice in one turn.
- [x] The closeout finalizer derives updated governance ids from actual final
      changed paths plus already-built packet/surface truth rather than broad
      repo scans.
- [x] Closeout supplemental selection suppresses overlap when an assist line
      already said the same thing with the same refs.
- [x] Voice guidance stays crisp, authentic, clear, simple, insightful,
      erudite in thought, soulful, friendly, free-flowing, human, and factual;
      silence beats filler, and humor only lands when the evidence makes it
      genuinely funny.
- [x] Runtime phrasing is still evidence-shaped and deterministic, but no
      longer leans on the same stock delta phrase across unrelated slices.
- [x] Shared and bundled guidance/skills use the same short-form command
      examples.
- [x] Install/on messaging points to the same first-turn grounding contract.
- [x] `odylith on` and `odylith off` describe their activation and fallback
      behavior plainly enough that operators do not need to infer what changes.
- [x] Focused CLI and install tests prove the alias and activation behavior.

## Non-Goals
- [x] Context Engine ranking or daemon-lifecycle changes.
- [x] Automatic background bootstrap reads on every shell open.
- [x] Wider shell/launchpad redesign in this slice.

## Impacted Areas
- [x] [component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md)
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [x] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [AGENTS.md](/Users/freedom/code/odylith/odylith/AGENTS.md)
- [x] [ODYLITH_CONTEXT_ENGINE.md](/Users/freedom/code/odylith/odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md)
- [x] [VALIDATION_AND_TESTING.md](/Users/freedom/code/odylith/odylith/agents-guidelines/VALIDATION_AND_TESTING.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-session-context/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-context-engine-operations/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/subagent-router/CURRENT_SPEC.md)
- [x] [odylith_chatter_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/odylith_chatter_runtime.py)
- [x] bundled mirrors under [src/odylith/bundle/assets/odylith](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [x] [test_agents.py](/Users/freedom/code/odylith/tests/unit/install/test_agents.py)
- [x] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [x] [test_render_registry_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_registry_dashboard.py)
- [x] [test_validate_component_registry_contract.py](/Users/freedom/code/odylith/tests/unit/runtime/test_validate_component_registry_contract.py)
- [x] runtime orchestration explanation proof under [tests/unit/runtime](/Users/freedom/code/odylith/tests/unit/runtime)
- [x] [test_odylith_assist_closeout.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_assist_closeout.py)
- [x] [test_odylith_benchmark_corpus.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_corpus.py)
- [x] [test_hygiene.py](/Users/freedom/code/odylith/tests/unit/runtime/test_hygiene.py)

## Risks & Mitigations

- [x] Risk: short-form commands drift from `odylith context-engine`.
  - [x] Mitigation: keep them as direct dispatch aliases into the existing
    Context Engine main surface.
- [x] Risk: `odylith bootstrap` still feels noisy on dirty repos and weakens
  - [ ] Mitigation: TODO (add explicit mitigation).
      trust.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: keep help text honest, preserve explicit widening signals,
      and leave deeper bootstrap intelligence for a later slice.
- [x] Risk: source and bundle guidance diverge.
  - [x] Mitigation: patch source-owned and bundled copies in the same change
      and keep install coverage on synced text.
- [x] Risk: richer conversation logic becomes templated and uncanny.
  - [x] Mitigation: emit structured facts plus suppression rules, keep fallback
      prose lightweight, and test for generic filler or repetitive branding.
- [x] Risk: Tribunal-aware chatter drifts into a hidden live reasoning step and
  - [ ] Mitigation: TODO (add explicit mitigation).
      slows the product or contaminates benchmark lanes.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: consume only precomputed Tribunal-backed delivery truth,
      cache any local artifact reads, and prove benchmark required paths and
      validation commands stay unchanged.
- [x] Risk: malformed or partial Tribunal-backed packet context leaks raw
  - [ ] Mitigation: TODO (add explicit mitigation).
      shapes into narration or makes the closeout sound uncanny.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: normalize explicit and cached Tribunal-backed chatter
      payloads before signal selection, fall back quietly when the shape is
      weak, and keep focused regression coverage on malformed inputs.
- [x] Risk: ambient and closeout composition quietly duplicate the same packet
  - [ ] Mitigation: TODO (add explicit mitigation).
      scans and metric work, adding invisible latency to every narrated turn.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: reuse precomputed request metrics and context-artifact
      rows inside one conversation-bundle pass, and keep a focused regression on
      that reuse contract.
- [x] Risk: closeout ids pick up unrelated dirty-worktree truth.
  - [x] Mitigation: accept a supplied final changed-path list in the closeout
      finalizer, and only fall back to bounded request seeds when exact final
      paths are unavailable.

## Validation/Test Plan
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py tests/unit/install/test_agents.py tests/integration/install/test_manager.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_render_registry_dashboard.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_render_registry_dashboard.py tests/integration/runtime/test_surface_browser_ux_audit.py`
- [x] `git diff --check`

## Rollout/Communication
- [x] Keep `odylith context-engine` documented as the full explicit namespace
      while making the short-form first-turn path the visible happy path.
- [x] Point install/on and AGENTS guidance at the same first-turn bootstrap and
      narrowing commands.

## Current Outcome
- [x] `B-031` landed and the plan is now closed into `done`.
- [x] Session-scope grounding now rescues prompt-derived path anchors and a
      bounded shared-path seed instead of degrading shared-only first turns to
      an empty grounded set.
- [x] Prompt-facing hot-path packets now suppress
      `working_tree_scope_degraded` receipts and fallback-scan scaffolding when
      Codex already has retained local anchors and can keep narrowing
      task-first.
- [x] `odylith on` now says plainly that Odylith-first guidance is restored and
      points operators back to the short-form bootstrap/context path.
- [x] `odylith off` now says plainly that Codex falls back to the surrounding
      repo's default behavior while the local runtime and `odylith/` context
      remain installed.
- [x] Repo-root managed AGENTS and consumer `odylith/AGENTS.md` now fail closed
      on substantive pre-grounding repo scans, keep grounding mostly in the
      background, and inline the same ordered workflow check.
- [x] Source-owned and bundled README/FAQ/runbook/spec text now describe the
      same on/off contract.
- [x] Source-owned and bundled AGENTS, guidelines, skills, and README text now
      require task-first consumer commentary while keeping the repo-local
      `odylith` step mandatory in the background.
- [x] Shared, bundled, maintainer, and benchmark-facing guidance now reserve
      Odylith-by-name narration for one optional end-of-work
      `Odylith Assist:` line that prefers bold Markdown when available. Lead
      with the user win, frame the factual edge against `odylith_off` or the
      broader unguided path, and stays backed by concrete counts, measured
      deltas, or validation outcomes.
- [x] Benchmark-facing mirrors now defer to `odylith-chatter` for the detailed
      closeout rubric so the benchmark lane keeps the rule as metadata-only
      instead of widening required reads just for branding.
- [x] Router and orchestrator human-readable reasons now describe scope,
      readiness, and blockers without `Odylith ...` control-plane chatter.
- [x] Registry now tracks `odylith-chatter` as the cross-posture narration
      contract so the closeout-branding rule has a first-class component
      boundary and living spec.
- [x] Shared orchestration runtime now emits one canonical
      `decision.odylith_adoption.closeout_assist` candidate so end-of-work
      Odylith branding is machine-built, evidence-backed, and suppressed when
      no user-facing delta is available.
- [x] Focused proof passed on 2026-03-30 via
      `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py tests/unit/install/test_agents.py tests/integration/install/test_manager.py`
      with `95 passed in 10.02s`, plus `git diff --check`.
- [x] Ambient conversation expansion landed under the same `B-031` owner:
      the runtime now emits a structured ambient/closeout bundle with linked
      governance ids and semantic suppression instead of one stock sentence.
- [x] April 7 polish follow-on landed under the same `B-031` owner: the
      runtime suppresses repetitive assist/supplement beats and avoids leaning
      on the same small stock phrase set across unrelated governed slices.
- [x] April 7 QA follow-on landed with browser and runtime proof that the
      shell-facing surfaces stay aligned with the quieter chatter contract and
      do not drift back into noisy, repetitive detail bands.
- [x] April 7 Tribunal follow-on landed under the same `B-031` owner:
      ambient chatter now reads precomputed Tribunal-backed delivery truth for
      stronger insight/risk/history beats, while keeping the path metadata-only
      for benchmarks and free of live Tribunal execution.
- [x] April 7 deep-dive hardening landed under the same `B-031` owner:
      explicit and cached Tribunal-fed chatter payloads now get normalized
      before narration, assist-less supplemental closeout lines stay
      suppressed, and the managed guidance contract drops one duplicated proof
      sentence.
- [x] April 7 efficiency follow-on landed under the same `B-031` owner:
      one conversation-bundle pass now reuses the same request metrics and
      context-artifact scan across ambient and closeout composition instead of
      repeating that packet work inside closeout.
- [x] Focused Tribunal-safe chatter proof passed on 2026-04-07 via
      `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_validate_component_registry_contract.py`
      with `56 passed in 5.64s`, plus `git diff --check`.
- [x] Deep-dive hardening proof passed on 2026-04-07 via
      `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/install/test_agents.py tests/integration/install/test_manager.py tests/unit/runtime/test_validate_component_registry_contract.py`
      with `109 passed in 6.12s`, plus
      `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_render_registry_dashboard.py`
      with `29 passed in 5.50s`, plus `git diff --check`.
