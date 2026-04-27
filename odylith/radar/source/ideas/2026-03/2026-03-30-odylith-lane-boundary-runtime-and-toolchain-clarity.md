---
status: finished
idea_id: B-027
title: Lane Boundary, Runtime, and Toolchain Clarity
date: 2026-03-30
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: constitutional docs, AGENTS activation, maintainer overlays, consumer bundle guidance, consumer write-policy enforcement, subagent routing and orchestration contract surfaces, component specs, backlog truth, Atlas runtime-boundary and orchestration diagrams, Atlas short-token search discoverability, and delivery-intelligence / Tribunal refresh behavior
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith now has the right runtime and self-host mechanics, but the execution model is still too easy to misread: which Python runs Odylith, which files can be edited, and which toolchain validates the target repo are distinct boundaries that need one explicit contract across maintainer and consumer lanes.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-30-odylith-lane-boundary-runtime-and-toolchain-clarity.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-004, B-005, B-016
workstream_blocks:
related_diagram_ids: D-014, D-020, D-021
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
Odylith's runtime isolation contract is correct, but the language around it is
still spread across docs and easy to collapse into one false question. Agents
and maintainers can still confuse:
- which Python runs the Odylith CLI
- which files the agent may edit
- which toolchain validates the target repo's own code

That ambiguity is especially risky in the Odylith product repo, where pinned
dogfood, detached `source-local`, maintainer-only overlays, and consumer-safe
guidance all coexist.

Some subagent-routing and orchestration surfaces also still read as if the
reasoning ladder were maintainer-only, even though the supported Codex lanes
already cover consumer work plus pinned dogfood and detached `source-local`
maintainer dev.

Consumer feedback also showed one adjacent operator gap: Atlas search could
miss diagrams when the operator entered a short numeric id token such as
`45`, `045`, or `-045` instead of the full `D-045` form.

## Customer
- Primary: Odylith maintainers working in the product repo and needing a crisp
  distinction between pinned dogfood proof and detached `source-local` source
  work.
- Secondary: consumer repos using Odylith inside Python, `uv`, Poetry, or
  Conda environments and needing confidence that Odylith runtime ownership does
  not replace project-toolchain ownership.

## Opportunity
If the lane contract becomes one explicit execution model instead of scattered
phrases, then maintainers and consumers can stop second-guessing whether
Odylith's managed Python prevents editing or validation. That should reduce
execution-time confusion and keep maintainers from falling back to ad hoc lane
selection or wrong validation habits.

## Proposed Solution
Publish one explicit lane matrix across constitutional docs, AGENTS guidance,
shared guidelines, shared and maintainer skills, component specs, backlog
truth, and Atlas diagrams:
- consumer lane
- product-repo maintainer mode
  - pinned dogfood posture
  - detached `source-local` dev posture

Make the three boundaries explicit everywhere:
- runtime boundary: which interpreter runs Odylith itself
- write boundary: which files the agent may edit
- validation boundary: which toolchain proves the target repo still works

Make consumer authority explicit too:
- grounding narrows diagnosis but does not authorize local Odylith mutation
- consumer write policy should be machine-readable as well as documented
- subagent routing should keep consumer Odylith fixes in diagnosis-and-handoff
  mode instead of local writes

Keep Atlas search discoverability aligned with that operator contract:
- Atlas search should match diagram ids even when the operator enters a short
  numeric suffix instead of the full canonical token

Keep dashboard and shell refresh honest too:
- missing Tribunal cache must fall back to deterministic reasoning instead of
  spawning opportunistic provider waits
- explicit Tribunal provider failures must degrade the rest of that run back to
  deterministic reasoning instead of repeating the same timeout across cases

## Scope
- create a new governed workstream and active plan for lane-boundary clarity
- update repo and Odylith constitutional guidance with one explicit lane matrix
- update shared guidelines and key shared skills to separate runtime, write,
  and validation boundaries
- update maintainer overlay guidance and skills to distinguish pinned dogfood
  from detached `source-local`
- update bundled consumer guidance so new installs inherit the same contract
- update component specs and Atlas diagrams to make the boundary durable
- apply the subagent reasoning ladder contract consistently across consumer,
  pinned dogfood, and detached `source-local` maintainer-dev surfaces
- harden delivery-intelligence and Tribunal runtime behavior so refresh and
  explicit reasoning flows match the written contract

## Non-Goals
- changing the underlying runtime implementation in this slice
- making consumer repos support `source-local`
- replacing target-repo validation with Odylith-managed Python

## Risks
- over-correcting and implying that pinned dogfood should execute live local
  `src/odylith/*` changes
- leaking product-maintainer-only guidance into bundled consumer assets
- leaving one old document with a conflicting command or mental model

## Dependencies
- `B-004` established the explicit product-repo self-host posture contract
- `B-005` established the consumer managed-runtime and rehearsal contract
- `B-016` established the consumer-safe versus maintainer-only guidance split

## Success Metrics
- constitutional docs describe the same three-boundary model and the same lane
  matrix without contradiction
- shared guidance and shared skills say that Odylith runtime choice does not
  control file-edit authority
- maintainer docs say clearly that pinned dogfood proves the shipped runtime,
  while detached `source-local` is the only live-source execution lane
- bundled consumer assets say clearly that Odylith may validate repo truth with
  Odylith commands, but repo code must still be validated with the consumer
  toolchain
- consumer installs carry an explicit no-mutate Odylith write policy that
  keeps consumer Odylith fixes in diagnosis-and-handoff mode unless the
  operator authorizes mutation
- Atlas diagrams and catalog metadata render the same execution model
- Atlas search matches short diagram-id tokens such as `45`, `045`, and
  `-045`
- subagent reasoning-ladder and orchestration surfaces say the same supported
  Codex lane coverage instead of reading as maintainer-only

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_agents.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_consumer_profile.py tests/unit/runtime/test_subagent_reasoning_ladder.py tests/unit/runtime/test_render_mermaid_catalog.py`
- `PYTHONPATH=src python -m pytest -q tests/integration/install/test_manager.py tests/integration/runtime/test_surface_browser_deep.py -k atlas`
- `make dev-validate`
- `./.odylith/bin/odylith atlas render --repo-root . --fail-on-stale`
- `git diff --check`

## Rollout
Ship as a contract-clarity slice. This should not change the supported runtime
behavior itself; it should eliminate the operator ambiguity around that
behavior.

## Why Now
The current ambiguity shows up exactly where Odylith should be strongest:
maintainer execution in the product repo and consumer execution inside repos
with their own Python toolchains. If the product cannot explain that split
crisply, execution discipline erodes at the moment it matters.

## Product View
Odylith should make the execution lane obvious before work starts. Runtime
ownership, file-edit authority, and target-repo validation should read as one
explicit contract, not a puzzle assembled from scattered notes.

## Impacted Components
- `odylith`
- `release`
- `dashboard`

## Interface Changes
- guidance and specs now describe a shared lane matrix instead of scattered
  one-off runtime statements
- maintainer overlays now say explicitly that pinned dogfood is proof posture
  and detached `source-local` is live-source execution posture
- bundled consumer assets now say explicitly that repo validation stays on the
  consumer toolchain
- subagent routing and orchestration surfaces now say explicitly that the
  reasoning ladder applies across consumer lane, pinned dogfood, and detached
  `source-local` maintainer dev

## Migration/Compatibility
- no runtime migration required
- no consumer behavior change required
- new installs simply receive clearer guidance
- dashboard refresh no longer waits on opportunistic provider reasoning when
  Tribunal cache is missing

## Test Strategy
- prove managed AGENTS injection still matches the updated lane text
- prove delivery-intelligence refresh stays deterministic without Tribunal cache
- prove explicit Tribunal runs stop retrying an unhealthy local provider across
  the rest of the queue
- rerender Atlas so the new boundary map becomes the shipped source of truth
- run diff hygiene after all mirrored bundle updates

## Open Questions
- whether a future slice should add a maintainer-only CLI helper for source
  lane selection so fewer source-tree tasks need direct module invocation

## Outcome
- Landed on 2026-04-07 and closed into `odylith/technical-plans/done/2026-03/2026-03-30-odylith-lane-boundary-runtime-and-toolchain-clarity.md`.
- Root guidance, maintainer overlays, bundled consumer assets, Registry specs,
  and Atlas now share one explicit runtime/write/validation boundary model
  across consumer, pinned dogfood, and detached `source-local` lanes.
- Consumer write-policy enforcement, Atlas short-id search, and deterministic
  delivery-intelligence or Tribunal degradation all shipped under the same
  owner with focused validation and rendered-surface proof.
