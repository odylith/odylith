Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-012

Goal: Restore Compass to provider-authored standup narration by default in
local agent environments, add Claude Code compatibility to the shared
reasoning adapter, and keep proof lanes deterministic.

Assumptions:
- Odylith runs inside a local coding agent most of the time.
- Deterministic fallback remains the fail-closed posture.
- Claude Code structured non-interactive JSON output is sufficient for the
  shared reasoning adapter boundary.

Constraints:
- Do not require hosted API keys for the default local Compass brief path.
- Do not let pytest or CI silently invoke external providers.
- Do not remove deterministic fallback or cache reuse.

Reversibility: Reverting this slice restores the old provider-unavailable
default and removes Claude Code local-provider compatibility without touching
tracked repo truth.

Boundary Conditions:
- Scope includes shared reasoning autodetect, Claude Code CLI provider support,
  Compass provider wiring, bug/workstream/plan truth, and Compass rerender
  proof.
- Scope excludes subagent spawn policy changes in Claude Code.

Related Bugs:
- [2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md)

## Context/Problem Statement
- [x] Compass global standup briefs were deterministic by default in Codex
  because the shared reasoning adapter still expected explicit endpoint config.
- [x] The shared Codex path also forced the stale legacy model alias
  `Codex-Spark 5.3`, which prevented the local provider from returning a brief
  even after autodetect was added.
- [x] The local standup brief cache never warmed when provider selection failed.
- [x] Claude Code had no compatible local provider adapter in Odylith reasoning.
- [x] Proof lanes still need deterministic behavior under pytest/CI.

## Success Criteria
- [x] Shared reasoning can infer a runnable local provider without endpoint
  config.
- [x] Codex can be selected automatically in Codex-hosted local usage.
- [x] The default local Codex path does not require a hardcoded host-model
  override.
- [x] Claude Code has a compatible local CLI reasoning provider.
- [x] pytest/CI proof lanes remain deterministic.
- [x] Compass runtime refresh uses the implicit local-provider path and can
  write a provider-backed standup brief cache.
- [x] The default Compass hot path stays bounded by warming the primary 24h
  global brief first instead of blocking on every window.

## Non-Goals
- [x] Removing deterministic fallback.
- [x] Changing Claude Code subagent spawn support.
- [x] Requiring hosted credentials for default local narration.

## Impacted Areas
- [x] [odylith_reasoning.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_reasoning.py)
- [x] [compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py)
- [x] [compass_standup_brief_narrator.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_standup_brief_narrator.py)
- [x] [test_odylith_reasoning.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_reasoning.py)
- [x] [test_compass_standup_brief_narrator.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_standup_brief_narrator.py)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/casebook/bugs/INDEX.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)

## Traceability
### Runtime Contracts
- [x] [odylith_reasoning.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_reasoning.py)
- [x] [compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py)
- [x] [compass_standup_brief_narrator.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_standup_brief_narrator.py)

### Governance Truth
- [x] [2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md)
- [x] [2026-03-29-odylith-local-provider-autodetect-and-compass-ai-brief-recovery.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-03/2026-03-29-odylith-local-provider-autodetect-and-compass-ai-brief-recovery.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/casebook/bugs/INDEX.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)

### Tests And Proof
- [x] [test_odylith_reasoning.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_reasoning.py)
- [x] [test_compass_standup_brief_narrator.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_standup_brief_narrator.py)
- [x] [current.v1.json](/Users/freedom/code/odylith/odylith/compass/runtime/current.v1.json)

## Risks & Mitigations

- [x] Risk: the wrong local provider is selected when multiple CLIs exist.
  - [x] Mitigation: prefer the current host when detectable, then fall back to
    the single available CLI or the existing deterministic path.
- [x] Risk: tests or CI start invoking providers implicitly.
  - [x] Mitigation: suppress implicit local-provider calls whenever pytest or
    CI markers are present.
- [x] Risk: Claude Code JSON output is wrapped differently than Codex output.
  - [x] Mitigation: parse both direct JSON objects and `result`-wrapped JSON
    payloads in the local Claude adapter.

## Validation/Test Plan
- [x] `PYTHONPATH=src pytest -q tests/unit/runtime/test_odylith_reasoning.py tests/unit/runtime/test_compass_standup_brief_narrator.py`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_compass_dashboard --repo-root . --output odylith/compass/compass.html`
- [x] inspect `odylith/compass/runtime/current.v1.json` for a provider-authored
  global standup brief and warm cache output

## Rollout/Communication
- [x] Ship the adapter change as additive local-provider support.
- [x] Rerender Compass so the generated surface reflects the provider-backed
  standup path immediately.
- [x] Record the bug as closed now that the shared adapter and Compass path are
  corrected locally.

## Dependencies/Preconditions
- [x] Compass standup narration already had deterministic fallback and cache
  contracts in place.
- [x] The shared reasoning adapter already supported bounded Codex CLI and
  endpoint-backed providers.

## Edge Cases
- [x] No local provider available still yields deterministic fallback.
- [x] Explicit endpoint config still works when intentionally configured.
- [x] Claude Code output wrapped under `result` still parses into structured
  reasoning payloads.

## Open Questions/Decisions
- [x] Decision: implicit local-provider autodetect should prefer the current
  host when detectable because Odylith lives inside a provider already.
- [x] Decision: keep pytest/CI deterministic even after adding implicit local
  provider support.

## Current Outcome
- Shared Odylith reasoning can now infer a local Codex or Claude Code provider
  without separate API-key configuration.
- Compass runtime refresh now opts into that implicit local-provider path
  outside pytest/CI, so the global standup brief can be provider-authored and
  cached.
- The default live refresh now warms the 24h global brief first and lets the
  48h view reuse cache or stay deterministic until it has been warmed, which
  keeps sync materially faster on cold start.
- Claude Code now has a compatible local structured-output provider adapter in
  Odylith reasoning.
