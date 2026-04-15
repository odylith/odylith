status: implementation

idea_id: B-089

title: Claude Host Capability Layer Cli Backed Baked Hooks And Compatibility Surface

date: 2026-04-11

priority: P1

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: claude_host_runtime,runtime_common,runtime_surfaces,install_manager,claude_project_assets,slash_commands,agents_guidelines,tests

sizing: L

complexity: Medium

ordering_score: 100

ordering_rationale: Mirror the Codex capability+CLI-backed-hook parity (B-087, B-088) into the Claude lane so both first-class delegation hosts share the same dynamically introspected, CLI-backed posture, satisfying the operator directive to fully optimize Odylith to Claude when the host is detected as Claude.

confidence: High

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-11-claude-host-capability-layer-cli-backed-baked-hooks-and-compatibility-surface.md

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
Claude already exposes a richer native host surface than Codex, but too much of
that lane still lived in standalone `.claude/hooks/*.py` scripts and static
project-asset assumptions instead of the first-class Odylith runtime. That left
Claude less dynamically introspected and less uniformly CLI-backed than the new
Codex parity work, even though Claude is supposed to be the richer first-class
host.

## Customer
Odylith maintainers running Claude Code who need the Claude lane to preserve its
richer native capabilities while still following the same CLI-backed,
capability-aware product contract as the Codex lane.

## Opportunity
Mirror the Codex capability-layer pattern into Claude, bake the remaining Claude
hook scripts into first-class runtime modules, and make install/routing consume
a real Claude capability snapshot instead of a static project-asset guess.

## Proposed Solution
- add a Claude capability layer and `odylith claude compatibility` CLI surface
- migrate the shared Claude hook helpers into the runtime package
- bake the remaining Claude host hooks into `src/odylith/runtime/surfaces/`
  modules routed through `odylith claude ...`
- derive effective `.claude/settings.json` hook and permission state at install
  time
- document the Claude host contract and add focused proof coverage

## Scope
- Claude capability inspection and effective-settings derivation
- baked runtime modules for the remaining Claude host hooks
- thin CLI dispatch, project-asset rewiring, expanded slash commands, and
  focused tests
- the touched Claude host guidance and bundle mirrors

## Non-Goals
- do not regress the richer Claude-native primitives that already work
- do not change Codex behavior in the process
- do not widen into MCP or benchmark proof work beyond the Claude host lane

## Risks
- the settings flip can break Claude hook execution if the CLI-backed commands
  and permissions drift
- `cli.py` is already in the red zone, so dispatcher growth has to stay thin
- copying the Codex capability model too literally could erase real Claude/Codex
  asymmetries instead of documenting them

## Dependencies
- `B-083`, `B-084`, and `B-085` define the existing Claude host lane and thin
  dispatcher pattern
- `B-087` and `B-088` define the Codex capability-aware parity shape this slice
  mirrors

## Success Metrics
- the remaining live Claude hook scripts disappear in favor of first-class
  runtime modules and CLI dispatch
- install writes a deterministic capability-derived `.claude/settings.json`
- routing and compatibility reporting consume a real Claude capability snapshot
- focused Claude host and install tests stay green

## Validation
- run focused Claude capability, host-runtime, install, and CLI dispatch tests
- run the strongest local Claude host proof available for the rewired settings
  contract

## Rollout
- land the capability layer and baked runtime modules
- flip `.claude/settings.json` to the CLI-backed contract
- remove the old standalone hook scripts once the new path is proven

## Why Now
Codex parity is now capability-aware and CLI-backed. Claude has to meet the
same standard without losing the richer native host surface that makes it worth
supporting.

## Product View
Claude should feel like the richer first-class Odylith host, not a parallel
script lane hanging off checked-in project assets.

## Impacted Components
- `odylith`
- `dashboard`
- `release`

## Interface Changes
- add `odylith claude compatibility` and expand the CLI-backed Claude host
  command surface

## Migration/Compatibility
- live and bundled `.claude/settings.json` move to the CLI-backed hook contract
  and the effective settings snapshot becomes capability-derived

## Test Strategy
- add focused coverage for Claude capability inspection, host-runtime modules,
  install-time effective settings, and CLI dispatch

## Open Questions
- which permissions and slash-command additions are required to keep the
  rewired Claude host lane both safe and friction-free?
