status: queued

idea_id: B-002

title: Odylith Multi-Developer Repo Collaboration Architecture

date: 2026-03-27

priority: P0

commercial_value: 5

product_impact: 5

market_value: 4

impacted_lanes: both

impacted_parts: project/repo/workspace scope identity, stable actor attribution, collaboration contracts, local runtime state isolation, governance surface projections, comment durability, agent memory hygiene, and optional hosted collaboration augmentation

sizing: XL

complexity: VeryHigh

ordering_score: 70

ordering_rationale: Odylith needs a first-class collaboration architecture before multiple developers and agents can safely share one repo without confusing scope identity, authorship, comments, or memory authority.

confidence: high

founder_override: no

promoted_to_plan:

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-001

workstream_blocks:

related_diagram_ids: D-001,D-002,D-018,D-019,D-020

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Odylith now treats tracked repo files as canonical product truth and `.odylith/`
as disposable local runtime state, but the product still lacks an explicit
multi-developer collaboration architecture. It cannot yet cleanly distinguish
the product/project, the current repository, and the active workspace/session.
Authorship is inconsistent across surfaces, comments have no durable policy, and
the Context Engine has no explicit rule for what collaboration data should be
compiled into agent memory versus kept transient.

## Customer
- Primary: Odylith maintainers and contributors working concurrently in the
  same product repo with both humans and coding agents.
- Secondary: host repositories that want the same operating model after
  installing Odylith without losing local-first behavior.
- Tertiary: operators who need auditable authorship, scope labels, and
  decision summaries across Radar, Compass, Registry, Atlas, Casebook, and the
  shell.

## Opportunity
By defining a first-class collaboration model now, Odylith can become credible
for shared multi-developer operation without abandoning the local-first product
boundary. This is the chance to make repo identity, actor identity, workspace
isolation, durable governance notes, and optional hosted augmentation coherent
before ad hoc comments and authorship fields spread across the product.

## Proposed Solution
Keep `odylith/` as the only canonical tracked governance truth and keep
`.odylith/` as disposable local runtime state, then introduce a collaboration
contract that clarifies scope, authorship, and comment durability.

### Wave 1: Canonical scope and actor contracts
- define `project > repo > workspace` as the default Odylith scope hierarchy
- add tracked collaboration metadata with stable `project_id`, `repo_id`,
  `workspace_id`, and `actor_id` semantics
- map git identity, agent identity, and optional hosted identities into stable
  actor records instead of relying on free-form author strings
- make Dashboard and Compass derive repo labels and scope identity from the new
  contract instead of ad hoc shell text

### Wave 2: Cross-surface authorship and resolved annotations
- add durable authorship fields across Radar ideas, technical plans, Casebook
  bugs, Atlas catalog entries, Registry component records, and Compass timeline
  events
- persist only resolved annotation summaries as tracked product truth, with
  artifact links, actor ids, timestamps, and status
- treat raw discussion threads as transient local state or optional hosted data,
  not as first-class tracked repo truth

### Wave 3: Workspace-isolated runtime and agent memory hygiene
- key local collaboration state by workspace/worktree/session under `.odylith/`
  so multiple developers do not collide on drafts, live threads, presence, or
  locks
- teach the Context Engine to compile resolved summaries and durable decisions
  into engineering notes while excluding raw conversational exhaust from agent
  grounding
- keep legacy compatibility where needed, for example preserving Compass
  `author` strings while adding canonical `actor_id`

### Wave 4: Optional hosted augmentation without authority inversion
- add an optional hosted lane for live comments, presence, inboxes, or shared
  retrieval where it materially improves collaboration
- keep hosted state explicitly non-authoritative: repo truth remains canonical,
  hosted systems accelerate coordination and sync back distilled outcomes
- define failure modes where the hosted layer can disappear entirely without
  blocking local rendering, grounding, or governance workflows

## Scope
- canonical collaboration contract for scope identity and actor identity
- repo/product distinction in Dashboard, Compass, and derived runtime payloads
- durable authorship fields across governance source artifacts
- resolved-annotation model for comments and editorial decisions
- workspace-local transient state layout under `.odylith/`
- Context Engine ingestion rules for collaboration summaries versus raw threads
- optional hosted collaboration and retrieval augmentation contracts

## Non-Goals
- replacing git or markdown as the product source of truth
- making a hosted service the primary authority for Odylith governance
- storing raw, long-lived discussion threads in tracked repo files by default
- solving billing, enterprise tenancy, or final ACL policy in the first slice
- forcing host repositories to adopt hosted infrastructure before local-first flows
  work

## Risks
- scope confusion can persist if `project`, `repo`, and `workspace` are added
  inconsistently across surfaces
- authorship can become noisy if stable actor ids are layered on top of legacy
  fields without a clear compatibility policy
- collaboration notes can pollute agent grounding if raw threads leak into the
  Context Engine memory surfaces
- repo churn can rise if comment durability is too broad or if transient state
  is accidentally tracked
- hosted augmentation can drift from repo truth if synchronization is not
  explicitly one-way and fail-safe

## Dependencies
- `B-001` remains the prerequisite because Odylith first needs a credible public
  self-governing product boundary before it can define its multi-developer
  collaboration model
- existing shell, Compass, Context Engine, and repo-profile machinery can
  be reused as the initial compatibility layer rather than replaced outright
- Atlas topology updates will likely be needed to document the collaboration
  control plane once implementation starts

## Success Metrics
- every governed artifact can resolve a canonical `project_id`, `repo_id`, and
  relevant `actor_id`
- Compass and Dashboard can distinguish the product, current repo, and active
  workspace without ad hoc shell labels
- Radar, plans, Atlas, Registry, Casebook, and Compass expose authorship
  consistently enough for audit and routing
- Context Engine grounding prefers resolved summaries and durable decisions
  while excluding raw thread noise from agent memory
- multiple workspaces or worktrees can collaborate under `.odylith/` without
  clobbering one another
- the hosted lane can be disabled entirely without breaking core local-first
  workflows

## Validation
- `PYTHONPATH=src python -m odylith.runtime.governance.validate_backlog_contract --repo-root .`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_compass_dashboard_shell.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_consumer_profile.py tests/unit/runtime/test_tooling_context_retrieval.py tests/unit/runtime/test_update_compass.py`

## Rollout
Queue this workstream behind the active self-governance bootstrap, then execute
it in waves rather than as one broad rewrite.

### Wave sequencing
1. lock the tracked collaboration contract and scope model
2. land authorship fields and surface render plumbing
3. isolate workspace-local runtime state and memory-ingestion rules
4. add optional hosted augmentation only after the local-first model is stable

### Adoption posture
- public Odylith repo becomes the first implementation and proving ground
- installed host repositories adopt the model later through the product
  contract instead of inventing their own incompatible collaboration ledgers

## Why Now
Odylith is already trying to behave like a self-governing product. The next
failure mode is not missing markdown or missing surfaces, but ambiguity about
who authored what, which repo/workspace is being governed, and whether comments
or memory are helping or hurting agentic coding. The product should settle that
architecture before collaboration entropy becomes part of the runtime.

## Product View
Odylith should stay local-first and repo-authoritative, but it cannot pretend a
single-user mental model will survive real shared development. Local files
should remain the source of truth, hosted collaboration should stay optional,
and comments should only become durable when they are distilled into resolved
summaries that help humans and agents reason faster instead of trapping them in
conversation exhaust.

## Impacted Components
- `odylith`
- `dashboard`
- `compass`
- `radar`
- `registry`
- `atlas`
- `casebook`
- `odylith-context-engine`
- `subagent-router`
- `subagent-orchestrator`

## Interface Changes
- add a tracked collaboration contract for `project`, `repo`, `workspace`, and
  `actor` identity
- add durable authorship fields across governance source artifacts
- add resolved annotation records with artifact references and actor ids
- extend Compass runtime payloads and shell payloads with canonical scope
  identity instead of only shell labels
- add workspace-keyed transient collaboration state under `.odylith/`
- make Context Engine note ingestion explicitly summary-first rather than
  thread-first

## Migration/Compatibility
- preserve `odylith/` as tracked authority and `.odylith/` as rebuildable local
  state
- keep legacy author strings where needed during migration, but treat them as
  compatibility views over stable actor identities
- avoid breaking host repositories by making the first version additive and
  optional where possible
- allow hosted augmentation to remain absent, disabled, or partially deployed
  without breaking local-first behavior

## Test Strategy
- add contract and parser tests for collaboration metadata, actor resolution,
  and authorship fields
- add Dashboard and Compass rendering tests for project/repo/workspace labeling
  and actor display
- add Context Engine retrieval tests proving resolved summaries are useful and
  raw thread exhaust is excluded
- add workspace-isolation tests to ensure multiple sessions/worktrees do not
  overwrite one another under `.odylith/`
- add compatibility tests for legacy author fields and no-hosted-service
  operation

## Open Questions
- should resolved annotations live in one shared collaboration ledger or in
  per-surface sidecars close to each artifact type
- when Odylith introduces hosted collaboration, should it start with comments,
  presence, or shared review inboxes first
- should `repo_id` be install-generated, git-remote-derived, or source-owned in
  the tracked collaboration contract
- what is the cleanest merge strategy when two workspaces resolve competing
  summaries against the same artifact in parallel
- how much authorship should be attributed to the initiating human versus the
  executing agent on mixed human/agent artifacts
