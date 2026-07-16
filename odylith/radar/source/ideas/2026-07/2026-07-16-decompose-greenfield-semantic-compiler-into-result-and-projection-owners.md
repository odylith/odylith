status: queued

idea_id: B-144

title: Decompose Greenfield Semantic Compiler Into Result and Projection Owners

date: 2026-07-16

priority: P1

commercial_value: 3

product_impact: 5

market_value: 3

impacted_parts: domain intelligence,greenfield semantic compiler,preconfirm transaction

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Required to keep the shared semantic compiler maintainable after the current deterministic-confirmation hardening.

confidence: High

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
greenfield_semantic_compiler.py is 1,418 LOC and combines visible-result extraction, candidate selection, validation, and projection repair; transaction-safety fixes now touch it without a clear phase boundary.

## Customer
Odylith maintainers need a small, auditable semantic compiler so pre-confirm transaction behavior can change without coupling unrelated result-selection and repair paths.

## Opportunity
Split result selection and projection repair into dedicated owners while preserving the current pre-confirm contracts and avoiding duplicate semantic helpers.

## Proposed Solution
Create the workstream for Decompose Greenfield Semantic Compiler Into Result and Projection Owners and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for Decompose Greenfield Semantic Compiler Into Result and Projection Owners.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- Domain/compliance/policy risk: Semantic projection drift could reintroduce generic outcomes, evidence custody loss, or workstream repair after confirmation; preserve hash-bound pre-confirm semantics during extraction.
- Security posture: Keep extraction deterministic and host-model independent; do not add post-confirm parsing, provider calls, dynamic imports, or write-path widening.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
The root compiler is at or below 1,200 LOC; extracted owners have focused regression tests; the full greenfield prewrite and commit-only authority suites remain green.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Maintainers can change one semantic phase through an explicit owner with focused contract tests and a root compiler below the source-size limit.

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
