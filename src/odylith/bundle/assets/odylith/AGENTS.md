# Odylith AGENTS

Scope: applies to Odylith paths under `odylith/`.

## Purpose
- Keep Odylith guidance, runtime surfaces, and execution helpers product-owned.
- Keep Odylith behavior scoped to Odylith paths and Odylith-owned tasks.
- Keep bundled consumer guidance separate from upstream release-engineering
  instructions and source-repo-only workflows.
- In consumer repos, keep Odylith-fix requests in diagnosis-and-handoff mode
  instead of local Odylith patching.

## What Odylith Owns Here
- guidance under `odylith/agents-guidelines/`
- skills under `odylith/skills/`
- product overview docs at `odylith/*.md`
- runtime docs/assets under `odylith/runtime/`
- shell-wide surface assets under `odylith/surfaces/`
- surface-owned truth under `odylith/radar/`, `odylith/atlas/`, `odylith/compass/`, `odylith/registry/`, and `odylith/casebook/`
- repo-local governance truth under `odylith/technical-plans/`, `odylith/radar/source/`, `odylith/casebook/bugs/`, and `odylith/registry/source/`
- Registry-owned component dossiers under `odylith/registry/source/components/`

## Working Rule
- For work under `odylith/`, read this file first.
- For repo-owned paths outside `odylith/`, defer to the repo root guidance.
- When both apply, treat the repo root as authoritative for repo-owned policy and this file as authoritative for Odylith-owned product behavior.
- In repos that carry Odylith under `odylith/`, use the repo-local launcher `./.odylith/bin/odylith` for Odylith CLI workflows.
- When the launcher is absent in a consumer repo, the canonical first bootstrap
  and rescue command is `curl -fsSL https://odylith.ai/install.sh | bash`.
- Consumer installs are always in the consumer lane:
  - `./.odylith/bin/odylith` runs Odylith on Odylith's managed runtime
  - target-repo code still validates on the target repo's own toolchain
- When repo-root guidance points at Odylith governance or runtime behavior, this file and the nearest local `AGENTS.md` under `odylith/` are the authority for that slice.
- For installed consumer guidance, any substantive repo scan or code change outside trivial fixes must start from the repo-local Odylith entrypoint, with the active workstream, component, or packet kept in scope before raw repo search, tests, or edits.
- Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.
- Start substantive turns with `./.odylith/bin/odylith start --repo-root .`; it chooses the safe first lane and prints the exact next command when Odylith still needs narrower evidence.
- When you already know the exact workstream, component, path, or id, use `./.odylith/bin/odylith context --repo-root . <ref>` before raw repo search. Use `./.odylith/bin/odylith query --repo-root . "<terms>"` only after concrete anchors already exist. Keep `odylith context-engine ...` for advanced packet control.
- Default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` for routine backlog, plan, bug, spec, component, and diagram upkeep. Treat repo-root `.agents/skills/` shims and `odylith/skills/` as specialist overlays rather than as the default path.
- When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`, go straight to that CLI and keep any `.agents/skills` lookup, missing-shim, or fallback-path details implicit unless they change the next user-visible action.
- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`. Use `odylith compass deep-refresh` when you also want brief settlement. Keep `odylith sync` as the broader governance and correctness lane.
- Keep the default operating lane shared across Codex and Claude Code: repo-root guidance, the repo-local launcher, truthful `odylith ... --help`, and the grounded governance workflow should mean the same thing on both hosts. Add host-specific tips only when the host exposes a real native capability that materially reduces hops.
- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a runtime distinction matters.
- Keep normal commentary task-first and human. Weave Odylith-grounded facts into ordinary updates when they change the next move, and reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels for rare high-signal moments. Pick the strongest one or stay quiet.
- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the
  intervention-engine fast path. Treat `Odylith Assist:` as the chatter-owned
  closeout. Do not collapse those two layers into one ad hoc narration path.
- When the shared conversation-observation runtime earns a full
  `**Odylith Observation**` or `**Odylith Proposal**`, preserve those exact
  labels, keep the markdown warm and human, and keep the moment rooted in the
  original user prompt rather than Odylith's own pending/applied summary
  strings.
- Preserve the shipped shape too: Observation should look like
  `Odylith Assist`, which means one short labeled line. Proposal should be a
  short ruled block with the heading, a couple of lines, a few bullets, and
  the confirmation line.
- Keep one stable intervention identity across teaser, Observation, and
  Proposal for the same session-local moment. Later hooks may add evidence or
  surface the first eligible Proposal, but they must not make the same moment
  feel like a fresh branded interruption.
- For Codex and Claude checkpoint hooks, keep the full Observation,
  Proposal, and Assist bundle in hidden developer context for continuity, but
  surface the earned Observation/Proposal beat visibly at the hook moment.
  Stop is the fallback closeout lane, not the primary intervention moment.
- At closeout, you may add at most one short `Odylith Assist:` line if it helps the user understand what Odylith materially contributed. Prefer `**Odylith Assist:**` when Markdown formatting is available; otherwise use `Odylith Assist:`. Lead with the user win, link updated governance ids inline when they were actually changed, and frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Ground the line in concrete observed counts, measured deltas, or validation outcomes. Humor is fine only when the evidence makes it genuinely funny. Silence is better than filler. At most one supplemental closeout line may appear, chosen from `Odylith Risks:`, `Odylith Insight:`, or `Odylith History:` when the signal is real.
- For substantive tasks, follow this workflow check in order: read the nearest `AGENTS.md`; run the repo-local `odylith start`/`odylith context` step; identify the active workstream, component, or packet; then move into repo scan, tests, and edits.
- In consumer repos, grounding Odylith is diagnosis authority, not blanket
  write authority: if the issue target is Odylith itself, inspect, cite
  evidence, and hand off upstream unless the operator
  explicitly authorizes local Odylith mutation.
- Treat self-directed `odylith upgrade`, `odylith reinstall`,
  `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh`
  as forbidden Odylith-fix paths in consumer repos because they are writes,
  not neutral inspection.
- Use direct `rg`, targeted source reads, or standalone host search only when Odylith is unavailable, the task stays within the trivial-fix exception, or Odylith explicitly recommends widening or fallback.
- For substantive grounded repo work, treat backlog, plan, Registry, Atlas, Casebook, Compass, and session upkeep as part of implementation, not optional aftercare, but switch to evidence-and-handoff when the issue is Odylith itself in a consumer repo.
- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.
- Search existing workstream, active plan, related bugs, related components, related diagrams, and recent Odylith session or Compass context first; for consumer Odylith-fix requests, cite that evidence and hand it off instead of extending, consolidating, reopening, or creating Odylith truth locally.
- If grounded evidence shows the slice is genuinely new and it is repo-owned non-product work, create the missing workstream and bound plan before continuing non-trivial implementation; if the issue is Odylith itself in a consumer repo, produce a handoff-ready feedback packet instead.
- Keep intent, constraints, validation obligations, and major decisions alive through Odylith session packets and Compass updates so later turns accumulate context instead of restarting from scratch.
- `./.odylith/bin/odylith` choosing Odylith's runtime does not limit which repo
  files the agent may edit. Interpreter choice and file-edit authority are
  separate concerns.
- In Codex, treat routed or orchestrated native spawn as the default execution path for substantive grounded consumer-lane work unless Odylith explicitly keeps the slice local.
- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding and validation contract. Codex uses routed `spawn_agent` payloads; Claude Code uses Task-tool subagents plus the checked-in `.claude/` project assets.

## Source File Size Discipline
- For Odylith-owned hand-maintained source-of-truth fixes, follow the product
  repo file-size policy: `800` LOC soft limit, `1200` LOC refactor-plan
  trigger, `2000+` red-zone exception only, and a `1500` LOC ceiling for
  tests.
- When an Odylith-owned hand-maintained file is already beyond those
  thresholds, treat the next meaningful source-of-truth change as
  refactor-first work: decompose it into multiple focused files or modules
  with robustness, reliability, and reusability as explicit goals instead of
  extending the oversized file in place.

## Governance Contract
- For non-trivial work touching Odylith governance under `odylith/`, create or update the bound plan under `odylith/technical-plans/` per `technical-plans/AGENTS.md`.
- Do not continue non-trivial implementation unless the active slice is already bound to a valid Radar workstream under `odylith/radar/source/`, or you backfill that workstream in the same change.
- Review matching bug records under `odylith/casebook/bugs/` before implementation and record matching bug ids or `no related bug found` in the active technical plan or handoff.
- Before final handoff, reconcile lifecycle truth across the touched plan, workstream, bug, and rendered governance surfaces by following the source contracts under `odylith/`.

## Product Boundary
- Shared Odylith product code, shared guidance, and shared runtime/surface
  files under `odylith/` should be fixed in the upstream Odylith source tree
  first.
- In consumer repos, stop at diagnosis and handoff for Odylith
  product issues; do not patch `odylith/` or `.odylith/` locally as a
  self-directed fix.
- After a product fix lands there, refresh the local `odylith/` tree through
  operator-authorized lifecycle commands.
- Repo-local records under `odylith/radar/source/`,
  `odylith/technical-plans/`, `odylith/casebook/bugs/`, and
  `odylith/registry/source/` remain editable when they describe this repo's
  own workstreams, bugs, and governance state, but they are read-only for
  consumer Odylith-fix requests.

## Routing
- Context engine behavior: `agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`
- Grounding and narrowing: `agents-guidelines/GROUNDING_AND_NARROWING.md`
- Governance and delivery surfaces: `agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`
- Security and trust boundary: `agents-guidelines/SECURITY_AND_TRUST.md`
- Subagent routing and execution posture: `agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`
- Product surfaces and runtime: `agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`
- Validation and testing: `agents-guidelines/VALIDATION_AND_TESTING.md`
- Install, upgrade, and recovery: `agents-guidelines/UPGRADE_AND_RECOVERY.md`
- Workstream source contracts: `radar/source/AGENTS.md`
- Technical-plan lifecycle: `technical-plans/AGENTS.md`
- Bug-record lifecycle: `casebook/bugs/AGENTS.md`
- Registry source contracts: `registry/source/AGENTS.md`

## Specialist Skills
- Routine backlog, plan, bug, spec, component, and diagram upkeep should stay on `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` first.
- Repo-root `.agents/skills/` is the only Codex-specific shortcut surface worth curating, and only for the high-frequency CLI lane rather than as a mirror of the full specialist inventory.
Bundled consumer-safe and shared skills:
- `skills/odylith-casebook-bug-capture/`
- `skills/odylith-casebook-bug-investigation/`
- `skills/odylith-casebook-bug-preflight/`
- `skills/odylith-compass-executive/`
- `skills/odylith-compass-timeline-stream/`
- `skills/odylith-component-registry/`
- `skills/odylith-context-engine-operations/`
- `skills/odylith-diagram-catalog/`
- `skills/odylith-registry-spec-sync/`
- `skills/odylith-schema-registry-governance/`
- `skills/odylith-subagent-orchestrator/`
- `skills/odylith-subagent-router/`
- `skills/odylith-session-context/`
- `skills/odylith-delivery-governance-surface-ops/`
- `skills/odylith-security-hardening/`

## Consumer Boundary
- Bundled consumer `agents-guidelines/` and `skills/` intentionally exclude the
  Odylith end-to-end release process.
- Consumer repos should not invent or mirror upstream release guidance locally.
