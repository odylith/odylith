status: implementation

idea_id: B-141

title: Claude hook latency budget and fast-path startup

date: 2026-05-01

priority: P1

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Claude hooks, Codex hooks, managed runtime launcher, intervention engine, context engine startup, project guidance bundle, show/help fast paths

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Operator reports the product feels super slow on Claude during migration; this directly affects adoption and trust in the host adapter.

confidence: High

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-05/2026-05-01-cross-host-hook-latency-and-migration-hardening.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on:

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

## Problem
Claude Code sessions report Odylith as super slow because each turn can load a large guidance surface, many skills, and prompt/stop hooks before the model answers. A migration transcript on 2026-05-01 specifically called out heavy system surface, startup hook fallback work, and unnecessary shelling out for show-style prompts.

## Customer
Developers using Odylith through Claude Code in consumer repos and the Odylith product repo, especially during routine migration, show, help, and narrow diagnostic turns where latency dominates perceived product quality.

## Opportunity
Make Odylith feel native on Claude by enforcing a low-latency hook/startup budget, avoiding expensive prompt-turn work when no high-value intervention is available, and keeping show/help fast paths direct instead of fanning into broad tool calls.

## Proposed Solution
Add host-general prompt and startup fast paths: low-signal prompt hooks return before building intervention alignment bundles, SessionStart uses cached runtime state by default instead of running `odylith start`, show/help/capability prompts stay locked to direct stdout routes, Claude prompt-submit work collapses into one prompt-bundle hook, Codex PostToolUse records dirty events and defers governed refresh to Stop-time settlement, and generated launchers dispatch host hook commands directly to baked runtime modules instead of importing the full `odylith.cli` dispatcher first.

## Scope
- Define and land the bounded work for Claude hook latency budget and fast-path startup.
- Apply the same prompt hot-path gating to Codex so the fix is host-general rather than Claude-only.
- Keep the managed launcher public command contract intact while bypassing full CLI imports for baked host hook modules.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this active v0.1.13 workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No blocking dependency remains; the active technical plan carries the related bug and host-runtime scope.

## Success Metrics
Prompt-submit and stop hooks stay under a documented local latency budget on warm Claude sessions; plain show/help/status prompts avoid startup fanout; tests cover low-signal prompt fast paths; release notes can cite measured before/after latency for Claude and Codex hook paths.

## Validation
- 2026-05-01 local timing on the v0.1.13 source tree: low-signal direct hook modules returned empty in about 42-44 ms median for Claude prompt-context, Claude prompt-teaser, and Codex prompt-context; the full CLI fallback path dropped to about 106-116 ms median after lazy package imports.
- Focused runtime/install validation covers Claude prompt-bundle hidden/visible parity, automatic route locks, Codex deferred dirty-event checkpointing, Stop-time governed refresh settlement, low-signal prompt gates, direct launcher dispatch, host parity, Casebook migration validation, and generated launcher syntax.

## Rollout
- Execute through the bound v0.1.13 technical plan and keep the first implementation wave focused on hook latency, prompt hot-path gating, launcher dispatch, and governed migration capture.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Claude should get the same grounded value without every prompt paying for heavy context, auto-memory, or intervention status work. The product needs explicit hot-path budgets, measured hook latency, and deterministic bypasses for low-signal prompts and stdout-clean command intents.

## Impacted Components
- `odylith`

## Interface Changes
- None decided yet; record interface changes once implementation is scoped.

## Migration/Compatibility
- Existing consumer repos need no data migration. Upgrading installs the host-launcher preference fix, direct host-hook launcher dispatch, cached SessionStart behavior, prompt hot-path gating, and refreshed host guidance/bundle assets.

## Test Strategy
- Unit tests cover low-signal Claude and Codex prompt hooks skipping bundle construction, host-intervention support staying lazy on low-signal prompts, Claude prompt-bundle route locks and visible teaser preservation, SessionStart using cached runtime state by default, direct show/help/capability route locks, launcher bootstrap fallback preference, Codex dirty-event settlement, and direct host-hook launcher dispatch.

## Open Questions
- No blocking open question for lifecycle promotion; follow-up design work for a long-lived hook daemon remains deferred outside this release-critical slice.
