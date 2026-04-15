status: implementation

idea_id: B-097

title: Casebook Bug Capture Fail-Closed Evidence Contract and Cross-Host Guidance Hardening

date: 2026-04-15

priority: P0

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: bug authoring CLI, Casebook bug records, Codex/Claude bug-capture guidance, intervention bug-capture path

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Bug capture is currently allowed to publish placeholder truth into Casebook, which poisons governed memory and makes the product look authoritative when it is missing core evidence. The fix has to fail closed and stay shared across Codex and Claude.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-15-casebook-bug-capture-fail-closed-evidence-contract-and-cross-host-guidance-hardening.md

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
`odylith bug capture` can currently publish placeholder `TBD` fields into a
new Casebook record even when the caller does not yet have enough grounded
failure evidence. That poisons governed bug memory and makes the product look
authoritative at exactly the moment it should either gather more evidence or
fail closed.

## Customer
Odylith maintainers and operators who need Casebook bug records to be durable
engineering memory instead of placeholder shells that only look authoritative.

## Opportunity
Make bug capture trustworthy again by requiring a minimum grounded evidence set
before new Casebook truth is written, and keep that contract shared across
Codex, Claude, the public CLI, and automated casebook-create paths.

## Proposed Solution
Replace placeholder bug templates with a fail-closed intake contract, expand
the public `odylith bug capture` surface to accept structured bug evidence,
prevent automated call sites from emitting low-evidence records, and update
the shared bug-capture guidance so cross-host agents gather the required fields
before invoking the command.

## Scope
- Land the bounded backend, CLI, and automated call-site hardening for
  fail-closed bug capture.
- Update the shared Codex/Claude guidance surfaces for bug capture and bug
  preflight.
- Keep the first implementation wave narrow, test-backed, and tied to
  `CB-114`.

## Non-Goals
- do not widen the slice into a broader Casebook schema redesign
- do not add a title-only fallback lane back under automation or intervention

## Risks
- If the minimum evidence contract is too weak, placeholder-quality bug truth
  will continue in a less obvious form.
- If it is too strict, automated or fast-path capture flows may regress into
  unusable friction.

## Dependencies
- `CB-114` defines the concrete product failure that this workstream must
  eliminate.
- The active `0.1.11` release lane should carry the final fix because the
  current bug-capture contract is already shipping.

## Success Metrics
- Title-only bug-capture attempts fail closed with a precise missing-evidence
  error.
- New Casebook bug records stop containing placeholder `TBD` intake fields.
- Shared Codex/Claude guidance matches the backend minimum-evidence contract.

## Validation
- Run focused bug-authoring, intervention, and Casebook render validation for
  the touched paths once implementation lands.

## Rollout
- Bind the in-progress technical plan, land the backend and guidance updates,
  refresh Casebook, and carry the fix into `0.1.11`.

## Why Now
The shipped bug-capture path is currently writing low-evidence placeholder truth
into Casebook. That is a direct product-trust failure, not backlog hygiene.

## Product View
If Casebook is meant to be durable engineering memory, bug capture cannot be
allowed to emit records that are obviously incomplete on first render.

## Impacted Components
- `odylith`
- `casebook`

## Interface Changes
- `odylith bug capture` will gain structured intake-evidence flags and reject
  incomplete captures.

## Migration/Compatibility
- Existing bug files remain valid; the change only hardens new capture
  behavior and shared guidance.

## Test Strategy
- Add targeted regression coverage for missing-evidence rejection, structured
  bug rendering without placeholders, and intervention-engine fail-closed
  behavior.

## Open Questions
- What is the strongest minimum-evidence field set that stays usable without
  inviting placeholder truth through another route?
