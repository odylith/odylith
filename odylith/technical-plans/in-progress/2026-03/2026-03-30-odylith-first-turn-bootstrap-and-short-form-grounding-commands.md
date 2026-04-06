Status: In progress

Created: 2026-03-30

Updated: 2026-03-31

Backlog: B-031

Goal: Make Odylith harder for Codex to miss by exposing a short first-turn
grounding path at the top-level CLI and aligning repo-root AGENTS, skills,
guidance, and install/on/off messaging around that same contract, including an
explicit fallback-to-default-agent posture when Odylith is intentionally off.

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
- [ ] The first useful Odylith grounding verbs are still hidden under
      `odylith context-engine ...`.
- [ ] Repo-root AGENTS activation still says "use Odylith first" more clearly
      than it says exactly which command to run first.
- [ ] Consumer guidance still leaks control-plane chatter into visible agent
      updates instead of keeping Odylith first in the background.
- [ ] Shared and bundled skills still teach nested Context Engine commands even
      when a shorter top-level surface would be clearer.
- [ ] Install/on messaging does not yet leave operators with one obvious
      first-turn bootstrap path.
- [ ] `odylith off` does not yet say plainly that Codex falls back to the
      surrounding repo's default behavior while leaving Odylith installed.

## Success Criteria
- [ ] `odylith --help` exposes short-form top-level grounding commands for the
      first-turn happy path.
- [ ] Repo-root managed AGENTS text names `odylith bootstrap` plus the next
      narrowing moves explicitly.
- [ ] Consumer repo guidance makes substantive Odylith grounding a hard gate,
      keeps the active workstream/component/packet in scope, and allows
      background grounding without a fixed visible commentary prefix.
- [ ] Consumer-facing commentary and routed human-readable runtime notes stay
      task-first and avoid control-plane receipts except when an exact command
      or real blocker must be surfaced.
- [ ] Cross-lane closeout guidance allows at most one end-of-work
      `Odylith assist:` line, preferably `**Odylith assist:**` when Markdown is
      available, kept soulful, friendly, authentic, and factual. Lead with
      the user win, and keep it evidence-backed against `odylith_off` or the broader
      unguided path across consumer, maintainer, dogfood, and benchmark
      reviewer surfaces.
- [ ] Shared orchestration runtime emits a deterministic closeout-assist
      candidate so the final-only branding rule is enforced by one canonical
      composer instead of lane-by-lane improvisation.
- [ ] Shared and bundled guidance/skills use the same short-form command
      examples.
- [ ] Install/on messaging points to the same first-turn grounding contract.
- [ ] `odylith on` and `odylith off` describe their activation and fallback
      behavior plainly enough that operators do not need to infer what changes.
- [ ] Focused CLI and install tests prove the alias and activation behavior.

## Non-Goals
- [ ] Context Engine ranking or daemon-lifecycle changes.
- [ ] Automatic background bootstrap reads on every shell open.
- [ ] Wider shell/launchpad redesign in this slice.

## Impacted Areas
- [ ] [component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md)
- [ ] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [ ] [agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [ ] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [ ] [AGENTS.md](/Users/freedom/code/odylith/odylith/AGENTS.md)
- [ ] [ODYLITH_CONTEXT_ENGINE.md](/Users/freedom/code/odylith/odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md)
- [ ] [VALIDATION_AND_TESTING.md](/Users/freedom/code/odylith/odylith/agents-guidelines/VALIDATION_AND_TESTING.md)
- [ ] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/session-context/SKILL.md)
- [ ] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-context-engine-operations/SKILL.md)
- [ ] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/delivery-governance-surface-ops/SKILL.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/subagent-router/CURRENT_SPEC.md)
- [ ] [odylith_chatter_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/odylith_chatter_runtime.py)
- [ ] bundled mirrors under [src/odylith/bundle/assets/odylith](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith)
- [ ] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [ ] [test_agents.py](/Users/freedom/code/odylith/tests/unit/install/test_agents.py)
- [ ] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [ ] [test_render_registry_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_registry_dashboard.py)
- [ ] [test_validate_component_registry_contract.py](/Users/freedom/code/odylith/tests/unit/runtime/test_validate_component_registry_contract.py)
- [ ] runtime orchestration explanation proof under [tests/unit/runtime](/Users/freedom/code/odylith/tests/unit/runtime)
- [ ] [test_odylith_assist_closeout.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_assist_closeout.py)

## Risks & Mitigations

- [ ] Risk: short-form commands drift from `odylith context-engine`.
  - [ ] Mitigation: keep them as direct dispatch aliases into the existing
    Context Engine main surface.
- [ ] Risk: `odylith bootstrap` still feels noisy on dirty repos and weakens
      trust.
  - [ ] Mitigation: keep help text honest, preserve explicit widening signals,
    and leave deeper bootstrap intelligence for a later slice.
- [ ] Risk: source and bundle guidance diverge.
  - [ ] Mitigation: patch source-owned and bundled copies in the same change
    and keep install coverage on synced text.

## Validation/Test Plan
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py tests/unit/install/test_agents.py tests/integration/install/test_manager.py`
- [ ] `git diff --check`

## Rollout/Communication
- [ ] Keep `odylith context-engine` documented as the full explicit namespace
      while making the short-form first-turn path the visible happy path.
- [ ] Point install/on and AGENTS guidance at the same first-turn bootstrap and
      narrowing commands.

## Current Outcome
- [ ] Bound to `B-031`; implementation in progress.
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
      `Odylith assist:` line that prefers bold Markdown when available. Lead
      with the user win, frame the factual edge against `odylith_off` or the
      broader unguided path, and stays backed by concrete counts, measured
      deltas, or validation outcomes.
- [x] Benchmark-facing mirrors now defer to `odylith-chatter` for the detailed
      closeout rubric so the benchmark lane keeps the rule as metadata-only
      instead of widening required reads just for branding.
- [x] Router and orchestrator human-readable reasons now describe scope,
      readiness, and blockers without `Odylith ...` control-plane chatter.
- [x] Registry now tracks `odylith-chatter` as the cross-lane narration
      contract so the closeout-branding rule has a first-class component
      boundary and living spec.
- [x] Shared orchestration runtime now emits one canonical
      `decision.odylith_adoption.closeout_assist` candidate so end-of-work
      Odylith branding is machine-built, evidence-backed, and suppressed when
      no user-facing delta is available.
- [x] Focused proof passed on 2026-03-30 via
      `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py tests/unit/install/test_agents.py tests/integration/install/test_manager.py`
      with `95 passed in 10.02s`, plus `git diff --check`.
