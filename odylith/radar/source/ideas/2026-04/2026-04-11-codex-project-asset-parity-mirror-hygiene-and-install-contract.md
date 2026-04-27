status: implementation

idea_id: B-087

title: Codex Project-Asset Parity, Mirror Hygiene, and Install Contract

date: 2026-04-11

priority: P1

commercial_value: 3

product_impact: 4

market_value: 3

impacted_parts: odylith, install, project-root assets, execution-governance, subagent-router

sizing: L

complexity: Medium

ordering_score: 88

ordering_rationale: Queued through `odylith backlog create` from the current maintainer lane.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-11-codex-project-asset-parity-mirror-hygiene-and-install-contract.md

execution_model: standard

workstream_type: standalone

workstream_parent: 

workstream_children: 

workstream_depends_on: B-069,B-083,B-084,B-085,B-086

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
Odylith now has a rich Claude project-asset surface and a host-family runtime
ladder, but Codex still lacks the managed project-root assets, install-truth,
and contract language needed to treat Codex as a first-class project-native
host. The current bundle mirror is also already drifted on the Claude side,
which makes Codex parity unsafe to land on top of the existing asset contract
until the shared mirror hygiene is repaired first.

## Customer
Odylith maintainers and operators who need one truthful cross-host contract for
project-native assets, install behavior, and delegated execution posture across
Codex and Claude Code.

## Opportunity
Land the first Codex parity slice on the repo's existing project-root asset
sync path: repair the live-versus-bundle Claude drift, add managed Codex
project assets and skill shims, and make the docs plus specs explicit about
what Codex CLI project assets can do today versus what the current routed
`spawn_agent` host-tool contract still cannot do.

## Proposed Solution
Promote this workstream into an implementation-backed plan that:
- renames the misleading project-root sync helper so its host-neutral behavior
  is obvious,
- repairs the `.claude/` bundle mirror drift before any Codex copy is added,
- adds managed `.codex/` and `.agents/skills/` assets to both the live repo and
  the bundled project-root asset tree,
- updates install guidance, product docs, and Registry/spec language to
  distinguish Codex CLI custom project assets from the still-built-in-only
  routed `spawn_agent` tool contract, and
- proves the install plus asset shape with focused tests.

## Scope
- Repair shared project-asset mirror hygiene for the managed `.claude/` tree.
- Add the first Codex project-asset slice under `.codex/` and
  `.agents/skills/` on the existing project-root install path.
- Update product docs, guidance, and specs so the Codex host contract is
  explicit and accurate.
- Keep the first Codex wave bounded to guidance, install, project assets, and
  contract truth backed by focused tests.

## Non-Goals
- Do not change the routed `spawn_agent` payload schema or teach the router to
  emit named `.codex/agents/*` types in this slice.
- Do not claim a Codex `PreCompact`, custom statusline, or subagent lifecycle
  hook surface that the host does not support.
- Do not fold benchmark proof or Codex baked Python host surfaces into this
  first asset-contract wave.

## Risks
- Codex CLI project assets are newer and partially experimental, so the first
  slice must stay tight and document native-blocked gaps honestly.
- Installing Codex assets on top of a drifted `.claude/` mirror would entrench
  the wrong source-of-truth unless mirror hygiene is repaired first.
- Codex CLI custom project agents and the current routed `spawn_agent` tool are
  related but not equivalent contracts; flattening them would overclaim host
  capability.

## Dependencies
- `B-069` cross-host contract hardening and host-family ladder separation.
- `B-083`, `B-084`, and `B-085` for the current Claude-side project-asset
  surface and host-native parity baseline.
- `B-086` / `CB-102` path-normalization hardening so `.codex/...` and other
  dotfile project assets survive the changed-path pipeline cleanly.

## Success Metrics
- Fresh consumer install materializes the repaired `.claude/` assets plus the
  new `.codex/` and `.agents/skills/` trees without any extra install-specific
  Codex sync path.
- Managed docs and specs describe one truthful Codex project-asset contract,
  including trusted-project gating and the distinction between Codex CLI custom
  assets versus routed built-in-role spawning.
- Focused tests pin the live-versus-bundle mirror inventory, Codex asset shape,
  and install materialization.

## Validation
- Run focused install, bundle, runtime-regression, and contract-shape tests for
  the touched assets.
- Re-run the CB-102 changed-path regression coverage with `.codex/` and
  `.agents/` paths present.
- Run a Codex CLI `0.120.0+` live proof step that confirms the project-scoped
  `.codex/` layer and repo-scoped `.agents/skills/` shims are discoverable in
  a trusted repo.

## Rollout
- Bind the first Codex parity slice to `release-0-1-11`.
- Land mirror hygiene first, then the Codex asset tree and contract docs, then
  the focused test additions.
- Leave Codex baked Python host surfaces and any router-level named-agent
  selection proof to a later follow-on slice.

## Why Now
Codex CLI now supports repo-scoped project assets strongly enough that Codex
parity is real implementation work, not just documentation. The repo already
has the host-family runtime foundation, but the managed asset contract is still
one host behind and the shared `.claude/` mirror drift should be fixed before
that gap widens further.

## Product View
Odylith should expose one truthful cross-host project-native surface: shared
grounding through `AGENTS.md`, host-specific project assets where the host
supports them, and no overclaiming where the routed tool contract still lags
behind the host's native config surface.

## Impacted Components
- `odylith`
- `execution-governance`
- `subagent-router`
- `install`

## Interface Changes
- Rename `_sync_managed_project_claude_assets(...)` to the host-neutral
  `_sync_managed_project_root_assets(...)`.
- Add managed project-root Codex assets under `.codex/` and `.agents/skills/`.
- Add a new guidance file:
  `odylith/agents-guidelines/CODEX_HOST_CONTRACT.md`.

## Migration/Compatibility
- Install behavior stays additive because the project-root asset sync path
  already materializes the entire bundled project-root asset tree.
- Codex project assets require the repo to be trusted by Codex before the
  checked-in `.codex/` layer takes effect.
- The routed `spawn_agent` host-tool contract remains built-in-role only in
  this slice for compatibility with the current host integration.

## Test Strategy
- Add a parity inventory test that compares managed live `.claude/` files to
  the bundled `.claude/` mirror.
- Extend bundle/install tests to assert `.codex/`, `.agents/skills/`, and the
  repaired `.claude/` assets materialize through the existing project-root
  sync path.
- Add Codex project-asset shape tests for config, agents, hooks, and skill
  shim layout.
- Keep the existing changed-path normalization regression active with Codex
  project assets present.

## Open Questions
- Which later bounded slice should own Codex baked Python host surfaces once
  the project-asset contract is green?
- When the host integration eventually proves named custom-agent selection end
  to end, should that land as a `subagent-router` contract extension or as a
  separate host-capability slice?
