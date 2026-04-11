---
status: implementation
idea_id: B-084
title: Claude Delegation Runtime Parity - Host Capability, Model Ladder, and Claude-Native Surface Expansion
date: 2026-04-11
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: execution host capability contract, agent runtime profile ladder, subagent router delegation fields, Claude subagent frontmatter, agents-guidelines routing doc, .claude/ project surface expansion including output styles, statusline, and PreCompact hook, slash-command parameterization, and characterization tests
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: B-083 restored the Claude guidance surface, but a second-pass scan found one silent correctness bug that made the host-neutral execution-profile ladder degrade to an empty model on every Claude spawn, no Claude-side column in the profile-to-model map, and several high-value `.claude/` surfaces still missing. This slice closes those gaps without regressing Codex.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-11-claude-delegation-runtime-parity-host-capability-model-ladder-and-claude-native-surface-expansion.md
execution_model: standard
workstream_type: standard
workstream_parent: B-083
workstream_children: B-085
workstream_depends_on: B-083
workstream_blocks:
related_diagram_ids: D-047
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
A post-`B-083` second-pass repo scan found that Claude delegation still silently
degrades at the runtime contract boundary even though the guidance surface has
been made first-class:

- `ExecutionHostProfile.detected(...)` and
  `host_runtime.host_capabilities(...)` both still declare
  `supports_explicit_model_selection=False` for the Claude host, while
  `execution_profile_runtime_fields(...)` in
  `src/odylith/runtime/common/agent_runtime_contract.py` treats that flag as a
  veto and returns an empty model for every Claude spawn. Claude Code does
  accept explicit model selection through subagent frontmatter and Task-tool
  spawns; the flag is defensively wrong.
- `_EXECUTION_PROFILE_RUNTIME_FIELDS` in the same module only carries Codex
  tuples (`gpt-5.4-mini`, `gpt-5.3-codex-spark`, `gpt-5.3-codex`, `gpt-5.4`).
  There is no Claude column, so even if the flag were flipped the profile
  ladder would have nothing to resolve to.
- All 8 Claude project subagents under `.claude/agents/` declare `model:
  sonnet` uniformly, which flattens review, retrieval, implementation, and
  correctness-critical leaves onto one middle tier.
- `odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md` still
  describes Codex as "the validated host today" while the rest of the
  contract now treats Claude as first-class, which leaks stale framing into
  every routed payload that reads the guidance file.
- Several high-value `.claude/` surfaces are still missing: no output-style
  contract for voice enforcement, no live `statusline.sh`, no `PreCompact`
  hook to preserve the active Odylith slice across context compaction.
- The 12 slash commands never use the documented `$ARGUMENTS` placeholder,
  so refs like `/odylith-context B-084` cannot be threaded through.
- Subagent `description:` frontmatter fields do not include the documented
  "Use PROACTIVELY when ..." clauses Claude's router reads to auto-dispatch
  work.
- `odylith-context-engine.md` still declares `tools: Read, Grep, Glob, Bash`,
  which lets a retrieval-only leaf widen into arbitrary shell execution.
- `src/odylith/runtime/orchestration/subagent_router.py` is 3,418 LOC,
  deep in the repo's own red-zone file-size policy; every future Claude
  tuning enters the same shared module and increases regression risk for
  both hosts.

## Customer
- Primary: operators who delegate through Claude Code and expect the
  Odylith execution profile ladder to route implementation, review, and
  retrieval work onto haiku, sonnet, and opus rather than a flat default.
- Secondary: Odylith maintainers who need the host-capability contract to
  reflect what Claude Code can actually accept, and need the guidance doc
  and routed guidance surfaces to say the same truth as `CLAUDE.md`.

## Opportunity
Finish making Claude delegation first-class inside the runtime contract and
the `.claude/` project surface: flip the host-capability flag, grow the
profile ladder with an explicit Claude column, differentiate subagent
frontmatter models, land the Claude-native surfaces that the Claude host
documents, and open the `subagent_router.py` decomposition so future Claude
tuning does not continue to deepen a red-zone shared file.

## Proposed Solution
- flip `supports_explicit_model_selection` to `True` for Claude in
  `src/odylith/runtime/execution_engine/contract.py` and
  `src/odylith/runtime/common/host_runtime.py`
- extend `_EXECUTION_PROFILE_RUNTIME_FIELDS` in
  `src/odylith/runtime/common/agent_runtime_contract.py` with a per-host-family
  layer that keeps the existing Codex tuples byte-identical and adds a Claude
  column (haiku for analysis/fast, sonnet for write, opus for frontier)
- update `execution_profile_runtime_fields` to resolve through the host-family
  axis, so Claude returns a real model instead of an empty string
- differentiate Claude subagent frontmatter models per profile semantics
- rewrite the "Codex is the validated host today" language in
  `SUBAGENT_ROUTING_AND_ORCHESTRATION.md:46` and list both Codex and
  Claude Code as validated delegation hosts
- add `.claude/output-styles/odylith-grounded.md` for voice-contract
  enforcement
- add `.claude/statusline.sh` plus `settings.json.statusLine` wiring to surface
  the active workstream, brief freshness, and provider posture
- add `.claude/hooks/pre-compact-snapshot.py` and register a `PreCompact` hook
  so the active Odylith slice survives context compaction
- parameterize `.claude/commands/*.md` with `$ARGUMENTS` where the command
  takes a ref
- add "Use PROACTIVELY when ..." clauses to each `.claude/agents/*.md`
  description
- drop `Bash` from `odylith-context-engine.md`'s declared tool list
- stand up a bounded decomposition plan for `subagent_router.py` so the
  future host-family + profile ladder growth does not continue to inflate a
  red-zone shared file
- add a characterization test that pins "each canonical profile resolves to
  a non-empty model for each validated host family"

## Scope
- `src/odylith/runtime/execution_engine/contract.py`
- `src/odylith/runtime/common/host_runtime.py`
- `src/odylith/runtime/common/agent_runtime_contract.py`
- `src/odylith/contracts/host_adapter.py` (if any shared field shape needs
  to carry through)
- `.claude/agents/*.md`, `.claude/commands/*.md`,
  `.claude/hooks/*.py`, `.claude/settings.json`, `.claude/output-styles/`,
  `.claude/statusline.sh`
- `odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`
- `tests/unit/runtime/` coverage for the host-family model map
- governance trail: Radar idea, technical plan, Casebook bug, Registry spec,
  Atlas diagram, Compass log

## Non-Goals
- decomposing `subagent_router.py` in this slice; document the decomposition
  workstream and its validation contract, but do not attempt the refactor
  here
- `.claude/mcp/` structured tool surfaces (explicitly excluded per the
  second-pass feedback cycle and operator direction)
- new benchmark proof against Claude; this slice is contract hardening and
  surface expansion, not measured proof

## Risks
- flipping `supports_explicit_model_selection` for Claude without a matching
  Claude model column would silently continue to return empty strings; the
  flag flip and the ladder must land together in one PR
- host-family profile growth inside the already red-zone
  `subagent_router.py` increases blast radius of a later accidental Codex
  regression; the decomposition workstream is the mitigation
- Claude subagent model differentiation may surprise operators used to the
  previous uniform `sonnet` posture; the voice-contract output style and
  statusline changes help make the new posture legible

## Dependencies
- `B-083` supplied the guidance-surface parity baseline and is the direct
  parent for this runtime-contract extension
- `CB-103` is the bug record created alongside this slice to track the
  silent model-selection flag regression

## Success Metrics
- `execution_profile_runtime_fields(profile, host_runtime="claude_cli")`
  returns a non-empty model for every canonical profile, with the Codex
  column byte-identical to its current tuples
- Claude project subagents resolve to differentiated models
  (haiku/sonnet/opus) through frontmatter that honors the profile ladder
- `.claude/` carries an active output style, statusline script, and
  `PreCompact` hook; `/odylith-context`, `/odylith-query`, and
  `/odylith-case` accept arguments via the documented `$ARGUMENTS`
  substitution
- routed guidance guidance now lists Codex and Claude Code as the two
  validated delegation hosts with no "until proven" Claude qualifier
- characterization test pins the new host-family axis so a future
  regression is caught before merge

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_host_runtime_contract.py tests/unit/runtime/test_agent_runtime_contract.py tests/unit/runtime/test_execution_governance.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/test_claude_project_hooks.py`
- `./.odylith/bin/odylith sync --repo-root . --check-only`
- `git diff --check`

## Rollout
Land the host-capability flip, the Claude profile-ladder column, and the
characterization test in one bounded commit first. Then land the
subagent frontmatter differentiation, the guidance doc rewrite, the
`.claude/` surface expansion, and the polish items. Close out by logging to
Compass so the next standup brief reflects the new runtime-contract posture.

## Why Now
`B-083` made the guidance surface first-class. Without the runtime-contract
fixes in this slice, every Claude delegation that touches the profile ladder
still drops its model silently, which is exactly the class of regression
`CB-084` closed for Codex-branded canon drift and exactly the class
`CB-103` captures for the Claude model-selection flag.

## Product View
Claude delegation should pay for the reasoning tier each leaf actually needs,
not for the uniform middle tier, and the runtime contract should not
silently block that by treating the host as "cannot select a model".

## Impacted Components
- `execution-governance`
- `subagent-router`
- `subagent-orchestrator`
- `odylith-context-engine`
- `odylith`

## Interface Changes
- `ExecutionHostProfile.supports_explicit_model_selection` becomes `True`
  for the Claude host family; downstream surfaces that read the flag can
  stop assuming Claude always returns an empty model
- `execution_profile_runtime_fields` now resolves through a
  `(host_family, profile) -> (model, reasoning_effort)` map; Codex column
  stays byte-identical
- Claude project subagents in `.claude/agents/` now declare per-profile
  model frontmatter instead of a uniform `sonnet`

## Migration/Compatibility
- Codex model ladder is unchanged; Codex callers see no diff
- Claude callers that previously received an empty model now receive a
  resolved Claude model name; callers that checked for empty string as a
  sentinel must be updated together with this change
- `.claude/` surface additions are additive; repos that opt out can ignore
  the new files

## Test Strategy
- add a characterization test that asserts every canonical profile resolves
  to a non-empty model for `codex_cli` and `claude_cli` host runtimes, and
  asserts the Codex tuples are byte-identical to the pre-change values
- extend existing Claude project hook tests to cover the PreCompact and
  statusline surfaces if they grow runtime dependencies

## Open Questions
- whether the profile-to-Claude-model map should be exposed through a
  dedicated helper so out-of-repo hosts can see the full host matrix, or
  whether it should remain private to the runtime module
