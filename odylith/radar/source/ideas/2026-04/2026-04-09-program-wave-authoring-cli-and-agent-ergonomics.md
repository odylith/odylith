---
status: finished
idea_id: B-079
title: Program/Wave Authoring CLI and Agent Ergonomics
date: 2026-04-09
priority: P2
commercial_value: 3
product_impact: 4
market_value: 2
impacted_parts: execution-wave authoring CLI, selector resolution, direct JSON-free program/wave maintenance, and coding-agent command ergonomics
sizing: M
complexity: Medium
ordering_score: 100
ordering_rationale: The sidecar matters because coding agents should not hand-edit execution-wave JSON, but the critical path is still the execution-governance engine itself. This workstream keeps the ergonomics thin and attached to the canonical contract instead of turning into a second planning system.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-12-program-wave-authoring-cli-and-agent-ergonomics.md
execution_model: standard
workstream_type: child
workstream_parent: B-072
workstream_children:
workstream_depends_on: B-073
workstream_blocks:
related_diagram_ids: D-031
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
Odylith can validate and render umbrella-wave programs, but coding agents still
have no ergonomic command surface for authoring them directly.

## Customer
- Primary: coding agents and maintainers authoring umbrella execution
  programs.

## Opportunity
Make the existing execution-wave contract easy to create, inspect, and update
without inventing a separate schema.

## Proposed Solution
- add `odylith program ...` and `odylith wave ...` commands
- make selector resolution fail closed
- emit `--json` output everywhere
- keep the sidecar contract thin and source-of-truth preserving

## Scope
- program and wave authoring commands
- command-oriented ergonomics for coding agents

## Non-Goals
- replacing release planning
- inventing a new program schema

## Risks
- the CLI could drift from the canonical JSON contract if it hides too much
  structure

## Dependencies
- `B-073`

## Success Metrics
- agents can create, inspect, and modify wave programs through CLI commands
- authoring remains fail closed

## Validation
- CLI and authoring round-trip tests

## Rollout
Land as a sidecar on top of the core execution-wave schema.

## Why Now
Execution-governance work is more useful if agents can use the program/wave
surface directly.

## Product View
This is ergonomics, not the main execution engine.

## Impacted Components
- `radar`
- `execution-governance`

## Interface Changes
- additive `odylith program` and `odylith wave` command families

## Migration/Compatibility
- additive and thin over the existing execution-wave file contract

## Test Strategy
- authoring CLI coverage

## Open Questions
- how much direct command advice should `odylith start` and related packets
  emit once the sidecar lands
