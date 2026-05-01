status: queued

idea_id: B-132

title: v0.1.15+ Collaboration Identity Workspace and Actor Model

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: B-002 collaboration architecture, repo/project/workspace identity, actor registry, git identity mapping, host-agent identity mapping, Compass timeline, Radar/Registry/Atlas/Casebook authorship, .odylith runtime isolation, and Context Engine session packets

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Stable identity is a prerequisite for shared context; without project, repo, workspace, and actor semantics, Odylith cannot safely coordinate multiple humans and agents across worktrees or future hosted augmentation.

confidence: high

founder_override: no

promoted_to_plan: 

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
Current Odylith governance records can describe work, components, and proof, but stable collaboration identity is not yet systematic across project, repo, workspace, actor, git user, host agent, optional hosted account, and session. As multi-agent and multi-developer operation expands, free-form author strings and unkeyed runtime state can blur ownership, pollute memory, and clobber transient collaboration state across worktrees.

## Customer
Primary customers are teams using multiple humans, Codex sessions, Claude sessions, and future harness adapters in one governed repo. Secondary customers are maintainers who need auditability across Radar, technical plans, Casebook, Atlas, Registry, Compass, and runtime memory.

## Opportunity
A stable identity model makes shared context trustworthy. It lets Odylith say who made or approved a decision, which workspace carried transient state, which actor owns a task, and which session generated evidence, while preserving local-first operation.

## Proposed Solution
Create the workstream for v0.1.15+ Collaboration Identity Workspace and Actor Model and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ Collaboration Identity Workspace and Actor Model.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Governed artifacts can resolve project, repo, workspace, and actor context. Compass and Dashboard display scope identity without ad hoc labels. Multiple worktrees or sessions do not overwrite drafts, locks, live presence, or session memory. Context Engine packets carry lane-fenced identity fields. Legacy records remain readable while new records prefer stable actor identifiers.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Implement the collaboration identity portion of the v0.1.15+ program as a direct continuation of B-002. Define project_id, repo_id, workspace_id, actor_id, session_id, and host_agent_id semantics. Keep legacy author strings as compatibility display fields, but make stable actor identity the governed routing and audit primitive. Transient collaboration state should be workspace-keyed under .odylith and excluded from tracked truth unless distilled into a durable summary.

## Impacted Components
- `odylith`

## Interface Changes
- None decided yet; record interface changes once implementation is scoped.

## Migration/Compatibility
- No migration impact recorded yet.

## Test Strategy
- Add targeted regression coverage when implementation begins.

## Open Questions
- Which existing workstreams or component specs should this attach to first?
