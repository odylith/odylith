---
status: queued
idea_id: B-036
title: Odylith Product Canon Tab for Feature Narrative
date: 2026-03-30
priority: P1
commercial_value: 5
product_impact: 4
market_value: 3
impacted_lanes: both
impacted_parts: shell navigation, product explanation, feature storytelling, release-adjacent marketing language, and durable articulation of what Odylith does for users
sizing: L
complexity: High
ordering_score: 99
ordering_rationale: Odylith can already do more than the current shell explains, but the product narrative is still scattered across release notes, onboarding copy, README text, and implicit surface affordances. A Product Canon tab would make the feature story explicit in product-marketing language without forcing users to reverse-engineer value from implementation detail.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-028,B-033
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
---

## Problem
Odylith's feature set is growing faster than its self-explanation. Today the
product story is fragmented across onboarding screens, release notes, README
copy, workstreams, and operator intuition. That makes it harder for users to
answer a simple question: what does Odylith do, and why should I care, in human
language instead of implementation detail?

## Customer
- Primary: new and returning users who need a crisp product narrative inside
  the shell itself.
- Secondary: maintainers shaping release notes, onboarding, and surface copy
  who need one durable feature story to draw from.
- Tertiary: evaluators and buyers who want product value explained clearly
  before they inspect the technical internals.

## Opportunity
By adding a Canon tab for feature narrative, Odylith can explain its value in a
way that feels intentional, reusable, and aligned across onboarding, release
storytelling, and everyday shell use.

## Proposed Solution
Add a Product Canon tab that captures Odylith's current feature set in clear
product-marketing language while staying grounded in real capabilities.

### Wave 1: Canon content model
- define the durable source format for product capabilities, value statements,
  and proof hooks
- separate user-facing product language from internal implementation detail and
  roadmap promises
- organize the canon by problem solved, not by internal module boundaries

### Wave 2: Shell presentation
- add a Product Canon tab with concise capability cards and deeper narrative
  detail
- make the surface feel like a deliberate product story, not a README copy-paste
- support updates as the product evolves without rewriting every surrounding
  surface

### Wave 3: Narrative reuse
- reuse Canon content in onboarding, release storytelling, and other shell
  explainers where it makes sense
- connect feature claims to proof points such as governed surfaces, benchmark
  posture, or release notes without turning the tab into a technical appendix
- add lightweight validation so product-language content stays structured and
  current

## Scope
- a dedicated Product Canon tab in the Odylith shell
- a governed source contract for feature narrative and value framing
- clear user-facing summaries of major Odylith capabilities
- reusable narrative blocks for onboarding and release-adjacent explanation
- traceable links from product claims to real product surfaces or proof points

## Non-Goals
- replacing technical docs, specs, or backlog records
- turning the first version into a full website or sales deck
- promising unreleased capabilities as if they already exist
- writing copy that ignores the actual product contract

## Risks
- product-marketing language can drift away from reality if it is not tied to
  governed proof
- the tab could become fluffy if it avoids specifics entirely
- over-reuse of Canon copy could make the shell repetitive instead of clearer
- a stale canon would make future product explanation less trustworthy

## Dependencies
- `B-028` is reshaping first-use experience and should draw from the same
  product narrative instead of inventing new wording ad hoc
- `B-033` already carries release-notes and product-explanation work that a
  Canon tab can strengthen and de-risk

## Success Metrics
- Odylith exposes one dedicated Product Canon tab in the shell
- users can understand the major Odylith capabilities without reading specs or
  plans first
- onboarding and release-adjacent explanation can reuse the same durable
  narrative blocks
- product claims stay grounded in real capabilities rather than roadmap hype
- maintainers have one stable place to update feature story as the product
  changes

## Validation
- `odylith sync --repo-root . --check-only`
- targeted tests for Canon payload shape, shell rendering, and narrative reuse
  points
- content-validation checks that ensure required fields exist and proof links
  resolve
- manual shell walkthrough of Canon, onboarding, and release-adjacent surfaces

## Rollout
Stand up the Canon content model first, ship the shell tab second, then reuse
the same narrative blocks in onboarding and release storytelling once the core
surface feels right.

## Why Now
Odylith now has enough real capability that weak explanation is becoming a
product limitation. If the shell cannot state the feature story plainly, users
will keep learning the product by inference instead of intention.

## Product View
The product should be able to say what it is in language that makes people want
to use it, without making them decode the repo first.

## Impacted Components
- `odylith`
- `dashboard`
- `release`
- `compass`

## Interface Changes
- add a Product Canon tab with capability summaries and deeper narrative detail
- introduce reusable product-story blocks that can power other shell
  explanation points
- expose stable deep links for Canon sections or feature groups
- add proof-link affordances so product claims can point at real surfaces

## Migration/Compatibility
- keep existing README, onboarding, and release-note content valid during the
  first rollout
- treat Canon as additive until surrounding surfaces intentionally reuse it
- keep technical documentation and product narrative separate even when they
  point to the same capability

## Test Strategy
- add contract tests for Canon content structure and required proof hooks
- add shell tests for Canon navigation and detail rendering
- verify reused narrative blocks stay synchronized across shell surfaces

## Open Questions
- whether the tab label should stay `Canon` or expand to something more obvious
  like `Product`
- how opinionated the tone should be before it stops feeling grounded
- which proof hooks are most useful for linking feature story back to real
  product behavior
