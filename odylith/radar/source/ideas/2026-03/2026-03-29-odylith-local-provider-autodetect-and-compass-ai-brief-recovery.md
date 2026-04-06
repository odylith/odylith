---
status: finished
idea_id: B-012
title: Odylith Local Provider Autodetect and Compass AI Brief Recovery
date: 2026-03-29
priority: P1
commercial_value: 4
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: shared reasoning adapter, local provider autodetect, Claude Code compatibility, Compass standup narration, and AI brief cache warming
sizing: M
complexity: Medium
ordering_score: 100
ordering_rationale: Compass was visibly underperforming because Odylith's shared reasoning defaults never selected the active local coding agent. That left Compass deterministic even inside Codex and fully incompatible with Claude Code for standup narration. Fixing provider autodetect, adding a Claude Code adapter, and warming the Compass AI brief path restores a core product-quality moment and aligns the product with the real local runtime environment.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-local-provider-autodetect-and-compass-ai-brief-recovery.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-001
workstream_blocks:
related_diagram_ids:
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Odylith's shared reasoning defaults assumed a hosted `openai-compatible`
provider even when Compass was already running inside a local coding agent.
That meant the global standup brief stayed deterministic in Codex by default,
the AI brief cache never warmed, the shared Codex path still forced the stale
legacy model alias `Codex-Spark 5.3`, and Claude Code had no compatible local
provider path at all.

## Customer
- Primary: Odylith operators expecting Compass to show the best AI-authored
  standup brief available in their local coding environment.
- Secondary: maintainers comparing Odylith-on versus Odylith-off and looking
  for an immediately visible product delta.

## Opportunity
If Odylith can infer the active local provider automatically and use it for the
shared reasoning boundary, Compass becomes materially better without asking for
API keys or extra setup.

## Proposed Solution
Add implicit local-provider autodetect to the shared reasoning adapter,
prefer the current host when detectable, add a Claude Code CLI structured
output provider, strip the stale legacy Codex model alias so the host can use
its current default automatically, keep pytest/CI proof lanes deterministic,
and route Compass runtime refresh through that implicit local-provider path so
the AI brief cache can warm and reuse the best available brief.

## Scope
- add implicit local-provider autodetect in shared Odylith reasoning
- add Claude Code CLI structured-output provider support
- keep proof lanes deterministic by suppressing implicit provider calls under
  pytest/CI
- route Compass runtime refresh through implicit local-provider selection
- keep the default Compass hot path bounded by warming the primary 24h global
  brief first and letting secondary global windows reuse cache or stay
  deterministic until warmed
- verify the rendered Compass payload shows provider-authored global standup
  briefs and writes the local brief cache

## Non-Goals
- replacing deterministic fallback
- changing subagent spawn policy in Claude Code
- introducing hosted API-key requirements into default local usage

## Risks
- auto-selecting the wrong local provider when multiple CLIs are installed
- allowing implicit provider calls to leak into pytest/CI proof paths
- parsing Claude Code structured output too narrowly

## Dependencies
- `B-001` established Compass and the shared Odylith runtime boundary

## Success Metrics
- default local Compass renders use the active local provider when available
- Codex environments no longer show `provider_unavailable` by default for the
  global standup brief
- Claude Code environments have a compatible local structured-output provider
  path
- pytest/CI proof lanes stay deterministic and do not call external providers
- `.odylith/compass/standup-brief-cache.v5.json` warms after a provider-backed
  Compass refresh

## Validation
- `pytest -q tests/unit/runtime/test_odylith_reasoning.py tests/unit/runtime/test_compass_standup_brief_narrator.py`
- `python -m odylith.runtime.surfaces.render_compass_dashboard --repo-root . --output odylith/compass/compass.html`

## Rollout
Ship as an additive shared-reasoning improvement and rerender Compass so the
generated surface reflects the provider-authored brief path immediately.

## Why Now
Compass is one of the clearest product-power moments. Leaving it stuck on a
deterministic fallback when Odylith is already inside a local provider makes
the product look weaker than it actually is.

## Product View
If Odylith is already living inside Codex or Claude Code, asking for another
AI provider config before Compass can sound smart is the wrong product.

## Impacted Components
- `compass`
- `odylith`
- `tribunal`

## Interface Changes
- shared reasoning now supports implicit local-provider autodetect
- Compass can source provider-authored standup briefs from Codex or Claude Code
  without separate endpoint configuration

## Migration/Compatibility
- additive only
- explicit endpoint config still works when intentionally configured
- deterministic fallback remains the fail-closed path when no runnable local
  provider exists

## Test Strategy
- unit-test provider autodetect and Claude Code adapter behavior
- rerender Compass and inspect the generated runtime payload

## Open Questions
- should Odylith eventually record the resolved local-provider name directly in
  the Compass runtime payload for clearer operator debugging
