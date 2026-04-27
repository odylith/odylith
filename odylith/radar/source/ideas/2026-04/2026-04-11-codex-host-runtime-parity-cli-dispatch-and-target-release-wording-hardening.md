status: implementation

idea_id: B-088

title: Codex Host Runtime Parity, CLI Dispatch, and Target-Release Wording Hardening

date: 2026-04-11

priority: P1

commercial_value: 3

product_impact: 3

market_value: 3

impacted_parts: codex host runtime, CLI dispatch, release wording, governance surfaces

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: The first Codex asset slice already landed in the current release; the next bounded move is to close the remaining runtime-host gap and normalize active target-release language on the touched surfaces before v0.1.11 ships.

confidence: medium

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-11-codex-host-runtime-parity-cli-dispatch-and-target-release-wording-hardening.md

execution_model: standard

workstream_type: standalone

workstream_parent: 

workstream_children: 

workstream_depends_on: B-087

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
The first Codex parity slice (`B-087`) shipped the project-root assets,
install contract, and truthful docs for `.codex/` plus `.agents/skills/`, but
the actual Codex host behavior still lived in standalone project-hook Python
files under `.codex/hooks/`. Claude already moved its host surfaces into
first-class runtime modules under `src/odylith/runtime/surfaces/` with a thin
`odylith claude ...` dispatcher, while Codex still relied on external scripts
that duplicated helper logic and were invisible to the product runtime
taxonomy.

At the same time, release wording remained easy to misread on active surfaces:
the repo's governed contract uses explicit `current` and `next` aliases for
release-planning selectors, but some human-facing copy still risked conflating
the `current` alias with "latest shipped GA".

## Customer
Odylith maintainers working in Codex who need the host lane to be as
CLI-backed, capability-aware, and release-legible as the Claude lane before
`v0.1.11` ships.

## Opportunity
Bake the supported Codex host behavior into first-class Odylith runtime
modules, expose it through a thin `odylith codex ...` CLI dispatcher, keep the
checked-in `.codex/` tree declarative, and normalize the touched active
surfaces to say `active target release` versus `latest shipped release` where
that distinction matters to operators.

## Proposed Solution
- add `src/odylith/runtime/surfaces/codex_host_*.py` modules for the supported
  Codex host behaviors
- add a thin `odylith codex` dispatcher in `src/odylith/cli.py`
- rewire `.codex/hooks.json` to call the CLI directly and remove the standalone
  `.codex/hooks/*.py` implementation lane
- add focused Codex host runtime tests and update the project-asset contract
- clarify touched guidance, runbook, and UI copy so release wording
  distinguishes the active target release from the latest shipped release

## Scope
- bake the supported Codex host hook behaviors into first-class runtime modules
- wire a thin `odylith codex` CLI surface
- convert `.codex/hooks.json` to CLI-backed commands
- update the matching bundle mirrors, docs, and focused tests
- normalize target-release wording on the active surfaces touched by this slice

## Non-Goals
- do not claim router-level named custom-agent parity through the current
  routed `spawn_agent` tool contract
- do not invent unsupported Codex-native surfaces such as `PreCompact`,
  subagent lifecycle hooks, or a custom statusline API
- do not rename the governed `current` / `next` release aliases or rewrite
  historical artifacts just to change wording

## Risks
- `src/odylith/cli.py` is already over the red-zone threshold, so growth must
  stay dispatcher-only
- Codex hook behavior must stay limited to the officially supported event set
- broad wording churn could damage the release-selector contract if it is
  treated as a global rename instead of an active-surface clarification

## Dependencies
- `B-087` for the checked-in Codex project assets and install contract
- `B-084` and `B-085` for the Claude-side parity reference shape and thin
  host-dispatch pattern

## Success Metrics
- Codex host behavior is implemented under `src/odylith/runtime/surfaces/`
  instead of standalone `.codex/hooks/*.py` logic
- `.codex/hooks.json` calls `./.odylith/bin/odylith codex ...` directly
- focused tests keep the Codex host runtime, hook contract, and touched
  wording stable
- the `v0.1.11` target-release story is explicit on the touched active
  surfaces

## Validation
- run focused unit coverage for the new Codex host runtime modules and the
  updated project-asset contract
- run focused CLI and governance validation for the touched dispatcher and
  release surfaces
- run `git diff --check`

## Rollout
- bind the slice to `release-0-1-11`
- land the runtime modules and thin dispatcher first
- rewire the project-root hooks to the CLI-backed contract
- update touched wording and validate the combined slice

## Why Now
The asset/install parity slice already landed, the user explicitly wanted Codex
parity inside the active `v0.1.11` target release, and the remaining gap was
architectural rather than speculative.

## Product View
Codex parity in `v0.1.11` is only credible if the runtime host layer matches
the rest of Odylith's product architecture and the release-facing language
stops implying that `current` means "latest shipped GA".

## Impacted Components
- `odylith`
- `release`

## Interface Changes
- add a thin `odylith codex ...` dispatcher and a first-class Codex
  compatibility inspection command

## Migration/Compatibility
- checked-in `.codex/hooks.json` moves to the CLI-backed contract and the
  effective consumer `.codex/config.toml` is derived from the local Codex
  capability snapshot

## Test Strategy
- add focused unit coverage for the baked Codex host runtime modules, project
  asset contract, and touched release wording surfaces

## Open Questions
- which touched active surfaces still need `active target release` wording once
  the host-runtime parity work lands?
