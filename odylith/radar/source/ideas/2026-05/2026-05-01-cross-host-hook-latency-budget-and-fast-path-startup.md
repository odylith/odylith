status: implementation

idea_id: B-141

title: Cross-host hook latency budget and fast-path startup

date: 2026-05-01

priority: P1

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Claude hooks, Codex hooks, managed runtime launcher, intervention engine, context engine startup, project guidance bundle, show/help fast paths

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Operator reports the product feels super slow on Claude during migration, and the same hot-path architecture can affect Codex and future hosts if prompt hooks, launcher dispatch, and governance settlement stay too heavy.

confidence: High

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-05/2026-05-01-cross-host-hook-latency-and-migration-hardening.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on:

workstream_blocks:

related_diagram_ids: D-002,D-018,D-020,D-037,D-038,D-041,D-042

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Claude Code sessions reported Odylith as super slow because each turn could load a large guidance surface, many skills, and prompt/stop hooks before the model answered. The same product risk exists for Codex and future host adapters whenever prompt context, launcher dispatch, dirty-event settlement, or intervention substrate checks pay full runtime cost on low-signal turns.

## Customer
Developers using Odylith through Claude Code, Codex, or future host adapters in consumer repos and the Odylith product repo, especially during routine migration, show, help, and narrow diagnostic turns where latency dominates perceived product quality.

## Opportunity
Make Odylith feel native across supported hosts by enforcing a low-latency hook/startup budget, avoiding expensive prompt-turn work when no high-value intervention is available, and keeping show/help fast paths direct instead of fanning into broad tool calls.

## Proposed Solution
Add host-general prompt and startup fast paths: generic low-signal prompt hooks skip the full conversation bundle and substrate receipt, Odylith-directed quiet prompts keep a compact substrate proof, SessionStart writes the same local alignment substrate to memory without duplicate stdout, show/help/capability prompts stay locked to direct stdout routes, Claude prompt-submit work collapses into one prompt-bundle hook, Codex PostToolUse records dirty events and defers governed refresh to Stop-time settlement, Claude exact non-governed Bash edits skip startup/checkpoint work, and generated launchers dispatch host hook commands directly to baked runtime modules with context-engine warm-daemon defaults.
Preserve the visible grounding sequence across hosts: `odylith start` is the first substantive turn gate, and `odylith context`, `odylith query`, `git status`, or broad repo search must wait until startup finishes and an exact anchor is known.
Use host-native surface controls where the host actually supports them: Claude
uses one prompt-bundle hook, async/filterable hook configuration, and
`disable-model-invocation` for manual workflow skills; Codex keeps to its
supported command-hook shape, concise `.agents/skills` metadata, and separate
dirty-event settlement without Claude-only fields.

## Scope
- Define and land the bounded work for cross-host hook latency budget and fast-path startup.
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
Prompt-submit and stop hooks stay under a documented local latency budget on warm host sessions; plain show/help/status prompts avoid startup fanout; tests cover low-signal prompt fast paths with memory, execution, delivery, Tribunal, and proof evidence; governed sync, dashboard refresh, Compass status, and owned surface refresh commands stay inside end-to-end latency budgets without provider-backed reasoning calls; release notes can cite measured before/after latency for Claude and Codex hook paths.

## Validation
- 2026-05-01 local timing on the v0.1.13 source tree: low-signal direct hook modules returned empty in about 42-44 ms median for Claude prompt-context, Claude prompt-teaser, and Codex prompt-context; the full CLI fallback path dropped to about 106-116 ms median after lazy package imports.
- Focused runtime/install validation covers Claude prompt-bundle hidden/visible parity, automatic route locks, Codex deferred dirty-event checkpointing, Stop-time governed refresh settlement, substrate-backed low-signal prompt gates, direct launcher dispatch, host parity, Casebook migration validation, and generated launcher syntax.
- Mixed-version fresh-host validation on 2026-05-02 proved current-source generated launchers remain accepted by the shipped v0.1.12 runtime health checker while keeping direct host-hook dispatch intact.
- Historical upgrade validation on 2026-05-02 proves consumer installs can upgrade from 0.1.10, 0.1.11, and 0.1.12 to the v0.1.13 target through the normal lifecycle. The 0.1.10 fixture applies the v0.1.11 value-engine migration from legacy signal-ranker state; the 0.1.11 and 0.1.12 fixtures skip it cleanly.
- End-to-end governed sync performance validation on 2026-05-02 runs full sync dry-run, all-surface dashboard refresh, Compass status, and owned Radar/Atlas/Registry/Casebook refresh commands in a temporary consumer repo under latency budgets. The same test installs a provider tripwire so accidental Codex, Claude, OpenAI, or Anthropic reasoning calls fail the test instead of silently burning credits.
- 2026-05-02 grounding-order hardening pins root guidance, install-generated
  guidance, Claude project bridge assets, Claude slash commands, Codex and
  Claude skill shims, source skills, and bundle mirrors to serial `start`
  before follow-on `context` or repo-inspection work.
- 2026-05-02 host-surface diet removed the duplicated Claude root contract
  from `CLAUDE.md`, made `.claude/CLAUDE.md` a pointer bridge, removed two
  no-op Claude prompt marker commands, made generated SessionStart hooks
  memory-only by default, suppressed generic low-signal receipts on Claude and
  Codex, and kept Odylith-directed quiet prompts plus visible prompt-bundle
  intervention paths intact.
- 2026-05-02 consumer-lane guidance diet reduced always-loaded managed
  guidance without removing capabilities: root `AGENTS.md` measured 21,291
  bytes after the pass, consumer `odylith/AGENTS.md` and its bundle mirror
  measured 16,211 bytes, and the hard-law kernel still names startup,
  Context Engine, Execution Engine, memory substrate, Tribunal, Intervention
  Engine, observers, governance, subagent routing, Surface DAGs, delivery,
  analysis, and migration-breakage observation.
- 2026-05-02 Claude skill curation uses the host-native
  `disable-model-invocation` field so only seven high-frequency skills remain
  model-invocable by default; twenty-eight lower-frequency workflows stay
  slash-invocable. Codex `.agents/skills` stays separate and unchanged.

## Rollout
- Execute through the bound v0.1.13 technical plan and keep the first implementation wave focused on hook latency, prompt hot-path gating, launcher dispatch, and governed migration capture.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Claude, Codex, and future host adapters should get the same grounded value without every prompt paying for heavy context or full intervention-bundle work. The product needs explicit hot-path budgets, measured hook latency, compact substrate proofs for quiet prompts, and deterministic bypasses for stdout-clean command intents.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `execution-engine`
- `governance-intervention-engine`
- `migration-runtime`
- `odylith-chatter`
- `subagent-orchestrator`
- `subagent-router`
- `radar`
- `casebook`
- `compass`

## Interface Changes
- None decided yet; record interface changes once implementation is scoped.

## Migration/Compatibility
- Existing consumer repos need no manual data migration. Upgrading from 0.1.10, 0.1.11, or 0.1.12 installs the host-launcher preference fix, direct host-hook launcher dispatch, memory-backed quiet SessionStart behavior, prompt hot-path gating, context-engine warm-daemon defaults, v0.1.12-compatible launcher-health anchors, refreshed host guidance/bundle assets, and any automatic release migration still required by local state.
- v0.1.13 also refreshes managed guidance and skill assets so supported hosts
  inherit the serial startup-grounding contract on upgrade.
- v0.1.13 keeps maintainer-only release and migration-observer guidance inside
  `odylith/maintainer/`; consumer installs receive the low-latency runtime and
  engine-preservation contract without product-repo release-gate obligations.

## Test Strategy
- Unit tests cover generic low-signal Claude and Codex prompt hooks skipping conversation-bundle and substrate construction, Odylith-directed quiet prompts keeping substrate evidence, Claude prompt-bundle route locks and visible teaser preservation, SessionStart using substrate state by default without duplicate hook stdout, direct show/help/capability route locks, launcher bootstrap fallback preference, legacy launcher-health parser compatibility, Codex dirty-event settlement, Claude exact non-governed Bash checkpoint skips, context-engine warm-daemon env defaults, and direct host-hook launcher dispatch.
- Integration tests cover 0.1.10 -> 0.1.13, 0.1.11 -> 0.1.13, and 0.1.12 -> 0.1.13 upgrade activation, migration-plan state, migration-result state, pin adoption, and runtime pointer convergence.
- Integration tests also cover governed sync/operator latency, no-provider credit burn, dashboard all-surface refresh behavior, and parallel multi-surface dashboard execution.
- Guidance tests cover serial start/context ordering across root guidance,
  install-generated guidance, Claude project assets, Codex/Claude skill shims,
  and source/bundle skill mirrors.
- Guidance and skill-surface tests also cover consumer guidance byte budgets,
  explicit engine-preservation language, Claude model-invocable skill capping,
  and Codex/Claude host separation.

## Open Questions
- No blocking open question for lifecycle promotion; follow-up design work for a long-lived hook daemon remains deferred outside this release-critical slice.
